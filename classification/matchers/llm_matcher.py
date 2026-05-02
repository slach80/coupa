"""
Stage 9: LLM-based classification for ambiguous cases
Handles confidence 0-70% cases using local Ollama or Claude API
"""

import json
import subprocess
from typing import Optional, Tuple, List, Dict
import os


class LLMMatcher:
    """
    Uses LLM to classify ambiguous invoices

    Strategy:
    - Load known activity codes from database
    - Prompt LLM with supplier + commodity + description
    - Get best code + top 3 alternatives with rationale
    - Confidence based on LLM certainty
    """

    def __init__(self, activity_codes_map: Dict[str, str], provider='ollama', model='llama3.1', ollama_host=None, fallback_to_opus=False):
        """
        Initialize LLM matcher

        Args:
            activity_codes_map: Dict of code → description
            provider: 'ollama' (local/remote, free) or 'claude' (API, paid)
            model: Model name ('qwen2.5-coder:7b-32k' for Ollama, 'claude-opus-4' for Claude)
            ollama_host: Remote Ollama host (e.g., 'http://192.168.1.70:11434')
            fallback_to_opus: If True, use Claude Opus when Ollama fails
        """
        self.activity_codes = activity_codes_map
        self.provider = provider
        self.model = model
        self.ollama_host = ollama_host or os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.fallback_to_opus = fallback_to_opus
        self.call_count = 0
        self.opus_call_count = 0
        self.cost = 0.0

        # Build activity code context for prompt
        self._build_code_context()

    def _build_code_context(self):
        """Build condensed activity code reference for prompt"""
        # Group by Level 1 type for better context
        self.code_context = "Activity Code Reference:\n"
        for code, desc in list(self.activity_codes.items())[:20]:  # Top 20 most common
            self.code_context += f"  {code}: {desc[:60]}\n"

    def match(self, supplier: str, commodity: str = '', description: str = '') -> Optional[Tuple[str, float, str, List[Dict]]]:
        """
        Match using LLM with optional Opus fallback

        Returns:
            Tuple of (best_code, confidence, rationale, alternatives) or None
        """
        if not supplier:
            return None

        # Build prompt
        prompt = self._build_prompt(supplier, commodity, description)

        # Try primary provider
        if self.provider == 'ollama':
            response = self._call_ollama(prompt)
        elif self.provider == 'claude':
            response = self._call_claude(prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        # Parse response
        if response:
            result = self._parse_response(response)
            if result:
                self.call_count += 1
                return result

        # Fallback to Opus if enabled and primary failed
        if self.fallback_to_opus and self.provider != 'claude':
            response = self._call_claude(prompt, model='claude-opus-4-20250514')
            if response:
                result = self._parse_response(response)
                if result:
                    self.opus_call_count += 1
                    return result

        return None

    def _build_prompt(self, supplier: str, commodity: str, description: str) -> str:
        """Build classification prompt"""
        prompt = f"""You are an IT spend classification expert. Given an invoice line, classify it to the correct IT Activity Code.

{self.code_context}

**Invoice to Classify:**
Supplier: {supplier}
Commodity: {commodity}
Description: {description}

**Instructions:**
1. Determine if this is IT-related spend
2. IT-related includes: software, hardware, cloud services, IT consulting, IT staffing, telecom/internet, cybersecurity, data services
3. NOT IT: office supplies, legal, advertising, utilities (electric/water), facilities, general consulting
4. If IT-related, assign the best activity code from the reference above
5. If NOT IT-related, return "NON_IT"
6. Provide confidence (0-100)
7. Give 1-sentence rationale

**Response Format (JSON):**
{{
  "code": "WP100",
  "confidence": 85,
  "rationale": "CDW supplying computer hardware maps to Client Computing",
  "alternatives": [
    {{"code": "IN100", "confidence": 60, "rationale": "Could be infrastructure if servers"}},
    {{"code": "WP230", "confidence": 45, "rationale": "Might be peripherals"}}
  ]
}}

**If non-IT spend:**
{{
  "code": "NON_IT",
  "confidence": 95,
  "rationale": "Office supplies are not IT spend"
}}

**Examples:**
- "Robert Half, Temporary Labor, IT contractor" → Find IT staffing/consulting code (IT-related)
- "Office Depot, Supplies, Paper and pens" → NON_IT
- "Comcast, Internet, Business internet" → Find Network/Telecom code (IT-related)
- "Electric Company, Utilities, Power bill" → NON_IT

Respond with JSON only, no other text."""

        return prompt

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Call Ollama model (local or remote)"""
        try:
            import requests

            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('response', '')
            else:
                print(f"⚠  Ollama error: {response.status_code} - {response.text}")
                return None

        except ImportError:
            print("⚠  Install requests: pip install requests")
            return None
        except requests.Timeout:
            print("⚠  Ollama timeout (30s)")
            return None
        except Exception as e:
            print(f"⚠  Ollama error: {e}")
            return None

    def _call_claude(self, prompt: str, model: str = None) -> Optional[str]:
        """Call Claude API"""
        # Requires ANTHROPIC_API_KEY environment variable
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            print("⚠  ANTHROPIC_API_KEY not set")
            return None

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)

            model_to_use = model or "claude-sonnet-4-20250514"

            response = client.messages.create(
                model=model_to_use,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            # Track cost (Opus: $15 input, $75 output per 1M tokens)
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            if 'opus' in model_to_use.lower():
                self.cost += (input_tokens * 0.000015) + (output_tokens * 0.000075)
            else:
                self.cost += (input_tokens * 0.000003) + (output_tokens * 0.000015)

            return response.content[0].text

        except ImportError:
            print("⚠  Install anthropic: pip install anthropic")
            return None
        except Exception as e:
            print(f"⚠  Claude API error: {e}")
            return None

    def _parse_response(self, response: str) -> Optional[Tuple[str, float, str, List[Dict]]]:
        """Parse LLM JSON response"""
        try:
            # Clean response (remove ANSI escape codes and control chars)
            import re
            cleaned = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', response)  # Remove ANSI codes
            cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)    # Remove control chars

            # Extract JSON from response (LLM might add text before/after)
            start = cleaned.find('{')
            end = cleaned.rfind('}') + 1

            if start == -1 or end == 0:
                return None

            json_str = cleaned[start:end]
            data = json.loads(json_str)

            code = data.get('code')
            confidence = float(data.get('confidence', 0))
            rationale = data.get('rationale', '')
            alternatives = data.get('alternatives', [])

            if not code:
                return None

            return (code, confidence, rationale, alternatives)

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"⚠  Failed to parse LLM response: {e}")
            print(f"   Response preview: {response[:200]}")
            return None

    def get_stats(self) -> Dict:
        """Get usage statistics"""
        return {
            'provider': self.provider,
            'model': self.model,
            'calls': self.call_count,
            'opus_calls': self.opus_call_count,
            'cost': self.cost
        }


if __name__ == '__main__':
    # Test the matcher
    from classification.database import Database, ActivityCode

    # Load activity codes
    db = Database('classification.db')
    session = db.get_session()
    codes = session.query(ActivityCode).all()
    activity_codes_map = {c.activity_code: c.activity_description for c in codes}
    session.close()

    # Initialize matcher (try Ollama first)
    matcher = LLMMatcher(activity_codes_map, provider='ollama')

    test_cases = [
        ('ODP BUSINESS SOLUTIONS LLC', 'Supplies (75000)', 'Office supplies'),
        ('FEDEX', 'Shipping - Operating (76010)', 'Package shipping'),
        ('ROBERT HALF', 'Temporary Labor (72500)', 'IT contractor staffing'),
        ('DUKE ENERGY', 'Utilities (73510)', 'Electric utility'),
    ]

    print("=" * 80)
    print("LLM MATCHER TEST")
    print(f"Provider: {matcher.provider}, Model: {matcher.model}")
    print("=" * 80)

    for supplier, commodity, description in test_cases:
        print(f"\nSupplier: {supplier}")
        print(f"Commodity: {commodity}")
        print(f"Description: {description}")

        result = matcher.match(supplier, commodity, description)

        if result:
            code, confidence, rationale, alternatives = result
            print(f"  → {code} ({confidence:.1f}%)")
            print(f"  {rationale}")
            if alternatives:
                print(f"  Alternatives: {len(alternatives)}")
        else:
            print(f"  → LLM failed to respond")

    print(f"\n{matcher.get_stats()}")
    print("=" * 80)
