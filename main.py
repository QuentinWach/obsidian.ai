import os
import csv
import re
import openai
from collections import Counter, defaultdict
from pathlib import Path
import datetime
import matplotlib.pyplot as plt
import numpy as np
import calendar
from api_keys import OpenAI_KEY

# Set your OpenAI API key
openai.api_key = OpenAI_KEY

def count_words(text):
    return len(text.split())

def extract_tags(text):
    return re.findall(r'#(\w+)', text)

def extract_links(text):
    return re.findall(r'\[\[(.+?)\]\]', text)

def get_creation_date(file_path):
    return datetime.datetime.fromtimestamp(os.path.getctime(file_path)).date()

def analyze_vault(vault_path):
    file_count = 0
    total_words = 0
    all_tags = []
    files_without_tags_or_links = []
    daily_stats = defaultdict(lambda: {'files': 0, 'words': 0})
    
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
                creation_date = get_creation_date(file_path)
                
                daily_stats[creation_date]['files'] += 1
                daily_stats[creation_date]['words'] += words
                
                if not tags and not links:
                    files_without_tags_or_links.append(file)
                
                csv_data.append({
                    'filename': file,
                    'word_count': words,
                    'tag_count': len(tags),
                    'link_count': len(links),
                    'tags': ', '.join(tags),
                    'creation_date': creation_date
                })
    
    tag_counts = Counter(all_tags)
    
    # Write CSV file
    with open('vault_metadata.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['filename', 'word_count', 'tag_count', 'link_count', 'tags', 'creation_date']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in csv_data:
            writer.writerow(row)
    
    # Write files without tags or links
    with open('files_without_tags_or_links.txt', 'w', encoding='utf-8') as f:
        for file in files_without_tags_or_links:
            f.write(f"{file}\n")
    
    return file_count, total_words, dict(tag_counts), files_without_tags_or_links, daily_stats

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

def github_style_plot(daily_stats, start_date, end_date):
    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(6, 2))

    # Calculate the number of weeks
    weeks = (end_date - start_date).days // 7 + 1

    # Create a matrix to hold our data
    activity_data = np.zeros((7, weeks))

    # Fill in the activity data
    for date, stats in daily_stats.items():
        if start_date <= date <= end_date:
            week_num = (date - start_date).days // 7
            day_num = date.weekday()
            activity_data[day_num, week_num] = stats['words']

    # Create the heatmap
    cmap = plt.cm.Greens
    im = ax.imshow(np.log(activity_data), cmap=cmap, aspect='auto')

    # Add white spacing between the cells
    ax.set_yticks(np.arange(7) - 0.5, minor=True)
    ax.set_xticks(np.arange(weeks) - 0.5, minor=True)
    ax.grid(which='minor', color='w', linestyle='-', linewidth=1.5)


    # Set up the axes
    ax.set_yticks(np.arange(7))
    ax.set_yticklabels(['Mon', 'Wed', "Tue", "Thu", 'Fri', "Sat", 'Sun'])  # Changed this line
    ax.set_xticks(np.arange(0, weeks, 4))
    ax.set_xticklabels([calendar.month_abbr[(start_date + datetime.timedelta(weeks=i)).month] 
                        for i in range(0, weeks, 4)])
    # Don't show the ticks only their labels
    ax.tick_params(which='both', width=0)
    ax.tick_params(which='major', length=10)
    ax.tick_params(which='minor', length=0)


    # Remove the frame
    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.title('Vault Activity (Word Count)')
    plt.tight_layout()
    plt.savefig('vault_activity_heatmap.png')
    plt.close()

def create_tag_frequency_plot(tag_counts, top_n=20):
    # Get the top N most common tags
    top_tags = Counter(tag_counts).most_common(top_n)
    tags, frequencies = zip(*top_tags)

    # Create the plot
    plt.figure(figsize=(6, 3))
    bars = plt.bar(range(len(tags)), frequencies, align='center', color="grey")
    plt.xticks(range(len(tags)), tags, rotation=45, ha='right')

    # Customize the plot
    plt.title(f'Top {top_n} Most Frequent Tags')
    #plt.xlabel('Tags')
    #plt.ylabel('Frequency')

    # Show no  axis and no top and right spine
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.gca().spines['left'].set_visible(False)

    # Show no left ticks
    plt.tick_params(left=False)
    # No left tick labels
    plt.yticks([])

    # Add value labels on top of each bar
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                 f'{height}',
                 ha='center', va='bottom')

    plt.tight_layout()
    
    # Save the plot as an image file
    plt.savefig('tag_frequency_plot.png', dpi=100, bbox_inches='tight')
    plt.close()

    print("Tag frequency plot saved as 'tag_frequency_plot.png'")


# =================================================================================================
# Main execution
vault_path = 'C:/Users/Quentin Wach/Documents/CloudVault'
file_count, total_words, tag_counts, files_without_tags_or_links, daily_stats = analyze_vault(vault_path)

print(f"Total files: {file_count}")
print(f"Total words: {total_words}")
print(f"Top 10 tags: {dict(Counter(tag_counts).most_common(10))}")
print(f"Files without tags or links: {len(files_without_tags_or_links)}")

# Create GitHub-style plot
end_date = max(daily_stats.keys())
start_date = end_date - datetime.timedelta(days=6*30)
github_style_plot(daily_stats, start_date, end_date)
create_tag_frequency_plot(dict(Counter(tag_counts).most_common(20)))

# Add tags to files without tags or links
#add_tags_to_files(vault_path, files_without_tags_or_links, list(tag_counts.keys()))