import aiohttp
import pandas as pd
from collections import defaultdict
import asyncio

async def call_gpt_api(prompt, api_key):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4-turbo",
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

async def process_alphabet(letter, group, topic_content_dict, api_key):
    prompt = f"Go through the entire list and return overly-similar topics. If no over-similar topics are found, or if the list is only one topic long, then return a blank output with no explanations. Only compare one topic with another. Only remove if two topics are extremely similar. For example, topic 1: health savings plan accounts topic 2: health saving accounts. In this case, health savings plan accounts would be removed. Even though these are not exactly identical, they contain very similar semantics. However, they must be VERY similar. If topics are different then do not remove. If topics are specifics of a different topic or under the umbrella of a particular topic, do not remove the specific topics or the other topics that fall under the umbrella. Return in the following format: 'removed_topic', 'topic_that_it_was_similar_to' (only one). Do not include any extra explanations or confirmations.: {group}"
    response = await call_gpt_api(prompt, api_key)
    results = []

    if response.strip():
        pairs = response.strip().split('\n')
        for pair in pairs:
            if not pair.strip():
                continue
            split_pair = pair.replace("'", "").split(', ', 1)
            if len(split_pair) == 2:
                removed_topic, kept_topic = split_pair
                results.append((removed_topic, kept_topic))
    return results

async def main():
    # Add your api key here.
    api_key = "YOUR API KEY HERE"
    # add the file path to your hot topics file here.
    file_path = 'YOUR PATH HERE'
    df = pd.read_html(file_path)[0]

    # creating dictionary from hot topics file
    topic_content_dict = dict(zip(df['topic'], df['content']))
    topics = sorted(df['topic'].unique())

    # splitting alphabetically
    alphabet_groups = defaultdict(list)
    for topic in topics:
        first_letter = topic[0].upper()
        alphabet_groups[first_letter].append(topic)

    tasks = [process_alphabet(letter, group, topic_content_dict, api_key) for letter, group in alphabet_groups.items()]
    responses = await asyncio.gather(*tasks)
    # If you want to see which terms the model identifies as redundant.
    # print(responses)

    for response in responses:
        for removed_topic, kept_topic in response:
            removed_content = topic_content_dict.pop(removed_topic, None)
            kept_content = topic_content_dict.get(kept_topic)
            if removed_content and kept_content:
                # prompt to merge content
                merge_prompt = (
                    f"Merge and summarize the following two content sections in a concise, medium-sized paragraph based off only the context of the content sections:\n\n"
                    f"1. {kept_content}\n\n2. {removed_content}\n\n"
                )
                merged_content = await call_gpt_api(merge_prompt, api_key)
                topic_content_dict[kept_topic] = merged_content
            elif removed_content:
                topic_content_dict[kept_topic] = removed_content

    print(topic_content_dict)

if __name__ == "__main__":
    asyncio.run(main())