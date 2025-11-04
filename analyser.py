import os
import openai
import pandas as pd
import google.generativeai as genai
from duckduckgo_search import DDGS
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
# client = OpenAI(api_key=os.getenv("GEMINI_API_KEY"))
# response = client.chat.completions.create(
#     model="gpt-4o-mini",
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant."},
#         {"role": "user", "content": "Hello!"},
#     ],
# )
# print(response.choices[0].message.content)
api_key = os.getenv("GEMINI_API_KEY")
print("GEMINI_API_KEY:", api_key)
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content("Hello, world!")
print(response.text)