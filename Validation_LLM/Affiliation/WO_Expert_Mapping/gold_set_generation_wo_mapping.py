import os
import csv
import json
import time
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# ── Import expert mapping dictionary ────────────────────────
from affiliation_mapping_dictionary import affiliation_list_map

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

curr_dir = os.path.dirname(os.path.abspath(__file__))
input_file = os.path.join(curr_dir, "affiliations_raw.csv")
output_file = os.path.join(curr_dir, "affiliation_gold_set.csv")


def get_relevant_mappings(affiliation: str, max_examples: int = 30) -> str:
    """
    Look up the affiliation in the expert mapping dictionary.
    Returns:
      1. An exact match if found (highest priority).
      2. Up to `max_examples` fuzzy-similar entries to give the LLM
         enough pattern context without blowing the token limit.
    """
    affil_lower = affiliation.lower()
    exact_matches = {}
    fuzzy_matches = {}

    for raw, normalized in affiliation_list_map.items():
        if raw.lower() == affil_lower:
            exact_matches[raw] = normalized
        elif any(token in raw.lower() for token in affil_lower.split() if len(token) > 3):
            fuzzy_matches[raw] = normalized

    # Build a readable block for the prompt
    lines = []
    if exact_matches:
        lines.append("# EXACT MATCH FOUND — use this mapping:")
        for raw, norm in exact_matches.items():
            lines.append(f'  "{raw}" -> {norm}')

    sample = dict(list(fuzzy_matches.items())[:max_examples])
    if sample:
        lines.append("# Similar mappings for context:")
        for raw, norm in sample.items():
            lines.append(f'  "{raw}" -> {norm}')

    if not lines:
        lines.append("# No close matches found in expert dictionary. Use your best judgement.")

    return "\n".join(lines)


BASE_SYSTEM_PROMPT = """You are an expert in data normalization and entity resolution. Your task is to normalize raw affiliation strings to standardized organization names.

You will be provided with:
  1. An expert-curated mapping dictionary (ground truth). If an exact match exists, YOU MUST use it.
  2. Similar mappings as pattern examples to guide fuzzy matching.

Rules to follow:
1. If an EXACT MATCH is provided in the mapping, return that normalized value. Do not deviate.
2. Normalize abbreviations and acronyms to full institution names.
3. Handle punctuation, spacing, and capitalization inconsistencies.
4. Recognize when brand names or departments belong to a parent company or university and map accordingly.
5. Account for multilingual or localized versions of university or organization names.
6. If an affiliation cannot be matched to any known mapping, return "Unknown".

Output:
Return ONLY the normalized name. No extra text, no quotes, no punctuation around it.
"""


def build_prompt(affiliation: str) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt) with the mapping injected."""
    mapping_block = get_relevant_mappings(affiliation)
    system = BASE_SYSTEM_PROMPT + f"\n\n# Expert Mapping Dictionary (relevant entries):\n{mapping_block}"
    user = f'Normalize this affiliation: "{affiliation}"'
    return system, user


def normalize_affiliation(affiliation, model="gpt-4.1", temperature=0):
    try:
        system_prompt, user_prompt = build_prompt(affiliation)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=150
        )

        result = response.choices[0].message.content.strip()

        # Strip any accidental markdown code fences
        if result.startswith('```json'):
            result = result.replace('```json', '').replace('```', '').strip()
        elif result.startswith('```'):
            result = result.replace('```', '').strip()

        # Handle unexpected JSON responses
        try:
            json_result = json.loads(result)
            if isinstance(json_result, dict):
                return json_result.get(affiliation, list(json_result.values())[0] if json_result else result)
            else:
                return result
        except json.JSONDecodeError:
            return result

    except Exception as e:
        print(f"  Error processing '{affiliation}': {e}")
        return "ERROR"


def load_existing_gold_set():
    """Load existing gold_set.csv if it exists and has data."""
    if not os.path.exists(output_file):
        return None
    try:
        validated = []
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                validated.append(row)
        return validated if validated else None
    except Exception as e:
        print(f"Warning: Could not read existing gold_set.csv: {e}")
        return None


def print_statistics(validated):
    N = len(validated)
    r = sum(1 for v in validated if v['label'] == 'r')
    w = N - r
    accuracy   = (r / N) * 100 if N > 0 else 0
    error_rate = (w / N) * 100 if N > 0 else 0

    print(f"\n{'='*70}")
    print(f"STATISTICAL VALIDATION")
    print(f"{'='*70}")
    print(f"N = Total manually evaluated: {N}")
    print(f"R = Correct (label=r):        {r}")
    print(f"W = Incorrect (label=w):      {w}")

    print(f"\n{'='*70}")
    print(f"1. ACCURACY")
    print(f"{'='*70}")
    print(f"Accuracy = R / N = {r} / {N} = {accuracy:.2f}%")

    print(f"\n{'='*70}")
    print(f"2. ERROR RATE")
    print(f"{'='*70}")
    print(f"Error Rate = W / N = {w} / {N} = {error_rate:.2f}%")

    correct_cases = [v for v in validated if v['label'] == 'r']
    if len(correct_cases) >= 20:
        print(f"\n{'='*70}")
        print(f"CONSISTENCY CHECK")
        print(f"{'='*70}")

        if not os.getenv("OPENAI_API_KEY"):
            print("Skipping consistency check: OPENAI_API_KEY not set")
            return

        print("Running consistency check on 20 correct samples (3 runs each)...\n")

        import random
        sample_cases = random.sample(correct_cases, min(20, len(correct_cases)))

        consistency_results = []
        inconsistent_count = 0
        total_variance = 0

        for idx, case in enumerate(sample_cases, 1):
            rfc_id   = case['rfc_id']
            original = case['original_affiliation']
            human_norm = case['human_normalized']

            print(f"[{idx}/20] RFC: {rfc_id} - Testing: {original}")

            runs = []
            for _ in range(3):
                result = normalize_affiliation(original, temperature=0)
                runs.append(result)
                time.sleep(0.5)

            all_same = all(r == runs[0] for r in runs)
            unique_outputs = len(set(runs))
            variance = unique_outputs - 1
            total_variance += variance
            if not all_same:
                inconsistent_count += 1

            consistency_results.append({
                'rfc_id': rfc_id,
                'original_affiliation': original,
                'human_normalized': human_norm,
                'run_1': runs[0], 'run_2': runs[1], 'run_3': runs[2],
                'unique_outputs': unique_outputs,
                'variance': variance,
                'consistent': 'Yes' if all_same else 'No'
            })

            print(f"  Run 1: {runs[0]}")
            print(f"  Run 2: {runs[1]}")
            print(f"  Run 3: {runs[2]}")
            print(f"  {'✓ Consistent' if all_same else '✗ Inconsistent'}\n")

        consistency_rate = ((20 - inconsistent_count) / 20) * 100
        avg_variance = total_variance / 20

        print(f"{'='*70}")
        print(f"Consistent outputs: {20 - inconsistent_count} / 20")
        print(f"Consistency rate:   {consistency_rate:.1f}%")
        print(f"Average variance:   {avg_variance:.2f}")

        consistency_file = os.path.join(curr_dir, "consistency_check.csv")
        try:
            with open(consistency_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['rfc_id', 'original_affiliation', 'human_normalized',
                              'run_1', 'run_2', 'run_3', 'unique_outputs', 'variance', 'consistent']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(consistency_results)
            print(f"\nConsistency results saved to: {consistency_file}")
        except Exception as e:
            print(f"ERROR saving consistency results: {e}")
    else:
        print(f"\nNot enough correct samples for consistency check (need 20, have {len(correct_cases)})")


def validate_normalizations():
    existing_data = load_existing_gold_set()
    if existing_data is not None:
        print(f"\nFound {len(existing_data)} entries in existing gold set. Skipping to stats...\n")
        print_statistics(existing_data)
        return

    print("No existing gold set found. Proceeding with validation...\n")

    if not os.path.exists(input_file):
        print(f"ERROR: Input file not found: {input_file}")
        return

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set!")
        return

    affiliations = []
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or 'rfc_id' not in reader.fieldnames or 'original_affiliation' not in reader.fieldnames:
                print(f"ERROR: CSV must have 'rfc_id' and 'original_affiliation' columns. Found: {reader.fieldnames}")
                return
            for row in reader:
                affiliations.append({'rfc_id': row['rfc_id'], 'original_affiliation': row['original_affiliation']})
    except Exception as e:
        print(f"ERROR reading input file: {e}")
        return

    if not affiliations:
        print("ERROR: No affiliations found in input file")
        return

    print(f"Total affiliations to process: {len(affiliations)}")
    print(f"Expert mapping dictionary loaded: {len(affiliation_list_map)} entries")
    print(f"Model: gpt-4.1\n")

    response = input("Proceed with normalization and validation? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return

    print(f"\n{'='*70}")
    print("VALIDATION INSTRUCTIONS:")
    print("  Press ENTER if LLM is correct  (label = r)")
    print("  Type correct name if wrong     (label = w)")
    print("  Type 'quit' to save and exit")
    print(f"{'='*70}\n")

    validated = []

    for i, item in enumerate(affiliations):
        rfc_id   = item['rfc_id']
        original = item['original_affiliation']

        print(f"\n[{i+1}/{len(affiliations)}] " + "="*50)
        print(f"RFC: {rfc_id}")
        print(f"Processing: {original}")

        # Show if there's an exact hit in the dictionary before calling the API
        if original in affiliation_list_map:
            print(f"  [Dict hit] -> {affiliation_list_map[original]}")

        print("Getting LLM normalization...")
        llm_normalized = normalize_affiliation(original, temperature=0)

        if llm_normalized == "ERROR":
            print("ERROR: Failed to get LLM normalization. Skipping.")
            if input("Press ENTER to continue or 'quit' to exit: ").lower() == 'quit':
                break
            continue

        print(f"\nOriginal:       {original}")
        print(f"LLM Normalized: {llm_normalized}")
        print("-"*60)

        human_input = input("Correct normalization (ENTER if correct, or type correction): ").strip()

        if human_input.lower() == 'quit':
            print(f"\nSaving progress... {len(validated)} validated.")
            break

        if not human_input:
            human_normalized = llm_normalized
            label = 'r'
            print("✓ Correct (label = r)")
        else:
            human_normalized = human_input
            label = 'w'
            print("✗ Incorrect (label = w)")

        validated.append({
            'rfc_id': rfc_id,
            'original_affiliation': original,
            'llm_normalized': llm_normalized,
            'human_normalized': human_normalized,
            'label': label
        })

        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['rfc_id', 'original_affiliation', 'llm_normalized', 'human_normalized', 'label']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(validated)
        except Exception as e:
            print(f"ERROR saving output: {e}")
            return

        if i < len(affiliations) - 1:
            time.sleep(0.3)

    if validated:
        print_statistics(validated)

    print(f"\nGold set saved to: {output_file}\n")


if __name__ == "__main__":
    validate_normalizations()
