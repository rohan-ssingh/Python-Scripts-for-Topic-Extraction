import aiohttp
import pandas as pd
from collections import defaultdict, Counter
import asyncio
import re

def split_document_into_chunks(document_text, chunk_size=2000):
    chunks = []
    current_chunk = []

    # Accumulate words into a chunk until the size limit is reached
    for word in document_text.split():
        if sum(len(s) for s in current_chunk) + len(word) + len(current_chunk) <= chunk_size:
            current_chunk.append(word)
        else:
            # Add the current chunk to the list and start a new chunk
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]

    # Add the final chunk if any words remain
    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

async def call_gpt_api(prompt, api_key):
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

# 

async def extract_topics(section_text, api_key):
    prompt = (
        """
            "Given a text section that is potentially relevant to answering users' questions about benefits options and a list of entity types, "
            "identify the most important entities of those types from the text, focusing on those that are crucial to understanding the section. Maximum of five, but if there are less important topics, than return less than 5."
            "The entities must be distinct, non-overlapping, and uniquely identifiable across documents, with comprehensive and concrete names rather than abbreviations. For example,  "
            "Topics must consist of more than one word and represent significant and specific concepts or information related to benefits, avoiding general descriptions, "
            "supporting details, or non-essential phrases. They should strictly adhere to the provided entity types: plan, recipient group, service provider, coverage information, "
            "plan features, and care type. Exclude topics that refer to time, date, weather, document or section references, or excluded entities such as Columbia University, "
            "Human Resources, or Columbia University Human Resources. Each topic must describe an entity or concept in a specific, actionable, and relevant manner, avoiding ambiguity. However, do not make topics too specific. "
            "or overgeneralization. "
            "or fewer if less relevant terms exist. Don't number the topics. Return each topic on a new line without any explanations or commentary. Return nothing but topics "
            "Returned topics should only be related to these entity types: plan, recipient group, service provider, coverage information, plan features, care type "
            "Return each topic on a new line, with no additional explanations or commentary:\n\n

            -Steps-
            1. Identify the most *important* entities, excluding \"Columbia University\", \"Human Resources\", \"Columbia Doctors\"\
            and \"Columbia University Human Resources.\" For each identified entity, extract the following information:

            - entity_name: Name of the entity

            Format each entity output as a new line with only the entity name:

            {document_text}

            ######################

            -Examples-
            Example 1: 
            Entity_types: plan, recipient group, service provider
            Below is the input text:

            ## Using an HSA

            ###  **Making the Most Out of Your HSA**

            [View Optum Webinar: Making the Most Out of Your Health Saving Accounts](https://www.optumbank.com/content/dam/optum3/optumbank3/resources/videos/making-the-most-hsa-webinar.mp4)

            ###  **Healthcare FSA vs. Health Saving Accounts (HSA)**

            See [HSA v. FSA: What are the differences? Comparison Chart](https://humanresources.columbia.edu/content/hsa-fsa-comparison "HSA v.FSA: What are the differences? Comparison Chart")

            ###  **HSA Restrictions**

            * Under IRS regulations, if you enroll in an HSA, you cannot participate in a Healthcare FSA (including rollover amounts).  

            * If your spouse participates in a Healthcare FSA that permits reimbursement of your unreimbursed medical expenses, you will _not_ be eligible to establish or contribute to an HSA until you are no longer covered by your spouse's Healthcare FSA.

            * You will not be eligible to establish or contribute to an HSA if you are covered by a medical plan option that is not an HSA-qualified HDHP (e.g., a spouse's employer's non-HDHP coverage).  

            * You can contribute to the HSA if you are over age 65, but only if you are not enrolled in any Medicare benefits (including Part A).

            ###################### 
            Output: 
            ```
            Health Savings Account
            Healthcare Flexible Spending Account
            Spouse
            Internal Revenue Service

            NOTE: These are just examples.
            ```
        """ 
        f"{section_text}"
    )
    response = await call_gpt_api(prompt, api_key)
    return [topic.strip() for topic in response.strip().split('\n') if topic.strip()]

async def generate_topic_description(topic, section_text, api_key):
    prompt = (
        f"Generate a concise, medium-sized description of the topic '{topic}' using the context from the following section:\n\n"
        f"{section_text}"
    )
    response = await call_gpt_api(prompt, api_key)
    return response.strip()

async def extract_top_topics(topics, api_key):
    prompt = (
        "Here is a list of topics. Identify the 25 most important, broad, and overarching topics that are potentially relevant to answering user questions about benefits options. DONT ADD ANY TOPICS. ONLY THE TOPICS GIVEN TO YOU IN THE LIST. If there are not 25 topics in the input, just return the topics."
        "Focus on general and widely applicable topics while avoiding overly specific or narrow ones. Return the top 25 topics in a new line without explanations (don't number the topics or add any additional explanations/descriptions):\n\n"
        f"{topics}"
    )
    response = await call_gpt_api(prompt, api_key)
    return [topic.strip() for topic in response.strip().split('\n') if topic.strip()]

async def clean_top_topics(topics, api_key):
    prompt = (
        f"Go through the entire list and return overly-similar topics. If no over-similar topics are found, or if the list is only one topic long, then return a blank output with no explanations. Only compare one topic with another. Only remove if two topics are extremely similar. For example, topic 1: health savings plan accounts topic 2: health saving accounts. In this case, health savings plan accounts would be removed. Even though these are not exactly identical, they contain very similar semantics. However, they must be VERY similar so for example. If topics are different then do not remove either. If you are removing two similar topics, keep the most descriptive one. If topics are specifics of a different topic or under the umbrella of a particular topic, do not remove the specific topics or the other topics that fall under the umbrella. Return the topic list without the overly-similar topics, so the final output should be the topics without the overly-similar ones. Do not number the topics. Do not include any extra explanations or confirmations.:"
        f"{topics}"
    )
    response = await call_gpt_api(prompt, api_key)
    return [topic.strip() for topic in response.strip().split('\n') if topic.strip()]

async def main():
    # Add your API key below
    # api_key = ""
    # test cases
    

    # Read the document content
    with open(file_path, 'r', encoding='utf-8') as file:
        document_text = file.read()
        print("File read.")

    # Step 1: Split document into logical sections
    sections = split_document_into_chunks(document_text, chunk_size=2000)
    print("Document split into chunks.")

    # Step 2: Extract topics for each section
    topic_dict = {}
    for section_text in sections:
        topics = await extract_topics(section_text, api_key)
        print("Topics extracted.")
        for topic in topics:
            if topic not in topic_dict:  # Avoid duplicates
                topic_dict[topic] = {}  # Initialize topic with an empty dict

    print("Topics in topic_dict:")
    for topic in topic_dict.keys():
        print(topic)

    # Step 3: Clean the extracted topics
    all_topics = "\n".join(topic_dict.keys())
    cleaned_topics = await clean_top_topics(all_topics, api_key)

    print("\nCleaned topics:")
    for topic in cleaned_topics:
        print(topic)

    # Step 4: Extract top 25 overarching topics from cleaned topics
    cleaned_topics_str = "\n".join(cleaned_topics)
    top_topics = await extract_top_topics(cleaned_topics_str, api_key)

    print("\nTop 25 overarching topics:")
    for topic in top_topics:
        print(topic)

if __name__ == "__main__":
    asyncio.run(main())
