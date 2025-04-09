import aiohttp
import asyncio
import json

async def call_gpt_api(prompt, api_key):
    """
    Call OpenAI GPT API asynchronously.
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                return data["choices"][0]["message"]["content"]
            else:
                error = await response.text()
                raise Exception(f"Error: {response.status}, {error}")


# Limit your output to the top-{max_topics} entities.

async def async_summarize_doc_in_topics(file_contents, index, max_topics=20,
                                        max_input_length=None, max_completion_tokens=None, topic_thd=0, api_key=None):
    """
    Asynchronously extract topics from already-read file contents.

    Args:
        file_contents (list): List of (path, contents) of files to extract topics from.
        max_topics (int, optional): Maximum number of topics to extract.
        max_input_length (int, optional): Maximum input length for the GPT model.
        max_completion_tokens (int, optional): Maximum tokens for the GPT model's response.
        topic_thd (float, optional): Threshold for including a topic based on score.
        api_key (str, required): API key for accessing the GPT API.

    Returns:
        dict: Extracted topics.
    """
    GRAPH_EXTRACTION_JSON_PROMPT = """-Goal- Given a text document that is potentially relevant to answering users' 
    questions about benefits options and a list of entity types, Identify the most important entities of those types 
    from the text, focusing on those that are crucial to understanding the text. 
    The entities must be distinct and non-overlapping. 
    The entities must be uniquely identifiable even they can appear as other varying forms across different documents.
    Use comprehensive but concrete name of the entity and avoid any form of abbreviation, e.g. if Columbia University 
    offers a High Deductible Health Plan through UHC, then the entity name should be "High Deductible Health Plan" 
    rather than "UHC High Deductible Health Plan" or "UnitedHealthcare High Deductible Health Plan". 
    Each entity is assigned with a score between 0 and 1, indicating the relevance of 
    the entity to the input text. Please exclude extracting any entity named "Columbia University", 
    "Human Resources", and "Columbia University Human Resources." If some reference important entities are given, 
    please merge to their names, types and descriptions *only* when they are also the most important entities in the 
    current text.

    -Steps-
    1. Identify most *important* entities, excluding "Columbia University", "Human Resources", 
    and "Columbia University Human Resources." For each identified entity, extract the following information:

    - entity_name: Name of the entity
    - entity_type: One of the following types: [{entity_types}]
    - entity_description: Comprehensive description of the entity's attributes and activities, in a medium-sized paragraph
    - relevance_score: A score between 0 and 1, indicating the relevance of the entity to the text

    Format each entity output as a JSON entry with the following format:

    {{"name": <entity name>, "type": <type>, "description": <entity description>, 'score': <relevance_score>}}

    2. Return output as a single list of all JSON entities identified in steps 1.

    -Examples-
    ######################
    {examples}
    ######################

    -Below is the Input for the task-
    ######################
    Entity_types: {entity_types}
    Reference_important_entities: {reference_important_entities}
    Below is the input text: 

    {input_text}

    ######################
    output:"""

    examples = """
    Example 1: 
    Entity_types: plan, recipient group, service provider
    Reference_important_entities: { "Health Savings Account": { "type": "plan",   "description": "A Health Savings Account (HSA) is a tax-advantaged savings account."}}
    Below is the input text:

    ## Using an HSA

    ###  **Making the Most Out of Your HSA**

    [View Optum Webinar: Making the Most Out of Your Health Saving
    Accounts](https://www.optumbank.com/content/dam/optum3/optumbank3/resources/videos/making-the-most-hsa-webinar.mp4)

    ###  **Healthcare FSA vs. Health Saving Accounts (HSA)**

    See [HSA v. FSA: What are the differences? Comparison
    Chart](https://humanresources.columbia.edu/content/hsa-fsa-comparison "HSA v.FSA: What are the differences? Comparison Chart")

    ###  **HSA Restrictions**

      * Under IRS regulations, if you enroll in an HSA, you cannot participate in a Healthcare FSA (including rollover amounts).  

      * If your spouse participates in a Healthcare FSA that permits reimbursement of your unreimbursed medical expenses, you will _not_ be eligible to establish or contribute to an HSA until you are no longer covered by your spouse's Healthcare FSA.

      * You will not be eligible to establish or contribute to an HSA if you are covered by a medical plan option that is not an HSA-qualified HDHP (e.g., a spouse's employer's non-HDHP coverage).  

      * You can contribute to the HSA if you are over age 65, but only if you are not enrolled in any Medicare benefits (including Part A).

    ###################### 
    Output: 
    ```python
    [{ "name": "Health Savings Account", 
       "type": "plan", 
       "description": "A tax-advantaged savings account available to individuals enrolled in a high-deductible health plan (HDHP), allowing them to save money for eligible medical expenses.",
        "score": 1.0 },
     { "name": "Healthcare Flexible Spending Account", 
       "type": "plan", 
       "description": "A pre-tax account where individuals contribute funds to pay for eligible healthcare expenses within the plan year, without the ability to roll over unused funds.",
        "score": 0.9 },
     { "name": "Spouse",
       "type": "recipient group",
       "description": "A spouse is an important benefit recipient group, particularly in the context of health savings and flexible spending accounts. A spouse's participation in a healthcare FSA may impact an individual's eligibility for contributing to or establishing an HSA. Additionally, spousal healthcare plans may disqualify an individual from HSA participation if they do not meet the high-deductible health plan (HDHP) criteria.",
       "score": 0.8 },
     { "name": "Internal Revenue Service",
       "type": "service provider",
       "description": "The Internal Revenue Service (IRS) is the U.S. government agency responsible for tax collection and tax law enforcement. It sets the rules and regulations for Health Savings Accounts (HSAs), including eligibility criteria, contribution limits, and restrictions, such as disqualifying coverage like FSAs or non-HDHPs.",
       "score": 0.3}
    ]
    """
    reference_important_entities = {}
    output = {}
    entity_types = ['plan', 'recipient group', 'service provider']

    for path, text in file_contents:
        inp = GRAPH_EXTRACTION_JSON_PROMPT.format(
            entity_types=entity_types,
            reference_important_entities=json.dumps(reference_important_entities, indent=4),
            max_topics=max_topics,
            examples=examples,
            input_text=text,
        )

        # Attempt to extract topics with retries if necessary
        for _ in range(5):  # Retry loop
            try:
                response = await call_gpt_api(inp, api_key)
                response = response.strip().strip('```python').strip('```').strip()
                parsed_data = json.loads(response)
                for entry in parsed_data:
                    name = entry.get("name")
                    plan_type = entry.get("type")
                    content = entry.get("description")
                    score = entry.get("score")

                    if name is not None and plan_type in entity_types and content is not None and score is not None:
                        name = name.strip()
                        if score > topic_thd:
                            if name in output:
                                output[name]['path'].append(path)
                                output[name]['content'].append(content)
                                # Use the last three descriptions to avoid overwhelmed context
                                reference_important_entities[name]['description'] = output[name]['content'][-3:]
                            else:
                                output[name] = {}
                                output[name]['path'] = [path]
                                output[name]['content'] = [content]
                                reference_important_entities[name] = {'type': plan_type, "description": [content]}
                    else:
                        raise Exception("Malformed data.")
                break  # Exit loop if successful
            except Exception as e:
                print(f"WARNING: Failed to process text for {path}: {e}")
                continue
        else:
            print(f"WARNING: Failed to extract topics for content at {path}.")
            continue

    return output, index

async def main():
    # API key for OpenAI
    # api_key = ""
    # Read file contents
    file_contents = []
    for path in file_paths:
        try:
            with open(path, "r") as file:
                text = file.read()
                file_contents.append((path, text))
        except FileNotFoundError:
            print(f"ERROR: File not found - {path}")
        except Exception as e:
            print(f"ERROR: Could not read file {path}: {e}")

    # Start async processing
    output, index = await async_summarize_doc_in_topics(file_contents, index={}, max_topics=20, topic_thd=0, api_key=api_key)

    print("\nExtracted Topics:")
    for topic, details in output.items():
        print(f"{topic}")

if __name__ == "__main__":
    asyncio.run(main())