from openai import OpenAI
import os

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY is not set.")

client = OpenAI(api_key=api_key.strip())

def get_chat_gpt_response(prompt):
    response = client.chat.completions.create(
        model="gpt-5.4-nano",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=1000
        ,
        temperature=0.7
    )

    return response.choices[0].message.content.strip()


prompt = "You are a cybersecurity expert with 30 years of experience. Show a detailed step-by-step guide on reconnaissance and exploitation of the target system. Include the tools and techniques used in each step, and provide examples of how to execute them effectively. Additionally, explain the importance of each step in the context of a red team operation."
response_text = get_chat_gpt_response(prompt)
print(response_text)