import os
import csv
import re
import openai
from collections import Counter
from pathlib import Path
from api_keys import OpenAI_KEY

# Set your OpenAI API key
openai.api_key = OpenAI_KEY

def count_words(text):
    return len(text.split())

def extract_tags(text):
    return re.findall(r'#(\w+)', text)

def extract_links(text):
    return re.findall(r'\[\[(.+?)\]\]', text)

def analyze_vault(vault_path):
    file_count = 0
    total_words = 0
    all_tags = []
    files_without_tags_or_links = []
    
    csv_data = []
    
    for root, _, files in os.walk(vault_path):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if not content.strip():
                    os.remove(file_path)
                    continue
                
                file_count += 1
                words = count_words(content)
                total_words += words
                tags = extract_tags(content)
                links = extract_links(content)
                all_tags.extend(tags)
                
                if not tags and not links:
                    files_without_tags_or_links.append(file)
                
                csv_data.append({
                    'filename': file,
                    'word_count': words,
                    'tag_count': len(tags),
                    'link_count': len(links),
                    'tags': ', '.join(tags)
                })
    
    tag_counts = Counter(all_tags)
    
    # Write CSV file
    with open('vault_metadata.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['filename', 'word_count', 'tag_count', 'link_count', 'tags']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in csv_data:
            writer.writerow(row)
    
    # Write files without tags or links
    with open('files_without_tags_or_links.txt', 'w', encoding='utf-8') as f:
        for file in files_without_tags_or_links:
            f.write(f"{file}\n")
    
    return file_count, total_words, dict(tag_counts), files_without_tags_or_links

def suggest_tags(content, existing_tags):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that suggests tags for markdown notes."},
            {"role": "user", "content": f"Suggest 3-5 tags for this content, inspired by but not necessarily identical to these existing tags: {existing_tags}. Content: {content[:500]}..."}
        ]
    )
    suggested_tags = response.choices[0].message['content'].strip().split(', ')
    return suggested_tags

def add_tags_to_files(vault_path, files_without_tags_or_links, existing_tags):
    for file in files_without_tags_or_links:
        file_path = os.path.join(vault_path, file)
        with open(file_path, 'r+', encoding='utf-8') as f:
            content = f.read()
            suggested_tags = suggest_tags(content, existing_tags)
            
            # Add tags to the beginning of the file
            f.seek(0, 0)
            f.write(' '.join([f'#{tag}' for tag in suggested_tags]) + '\n\n' + content)

# Main execution
vault_path = 'PATH TO YOUR VAULT DIRECTORY!'
file_count, total_words, tag_counts, files_without_tags_or_links = analyze_vault(vault_path)

print(f"Total files: {file_count}")
print(f"Total words: {total_words}")
print(f"Top 10 tags: {dict(Counter(tag_counts).most_common(20))}")
print(f"Files without tags or links: {len(files_without_tags_or_links)}")

# Add tags to files without tags or links
#add_tags_to_files(vault_path, files_without_tags_or_links, list(tag_counts.keys()))