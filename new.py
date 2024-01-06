from flask import Flask, render_template, request, redirect, url_for, send_file, session
#from flask_mysqldb import MySQL
import os
import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from textblob import TextBlob
import networkx as nx
from wordcloud import WordCloud
from PIL import Image
from langdetect import detect, LangDetectException
import re
import urllib.parse
import requests
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import io
from flask import send_file
from flask import render_template_string
from flask import g

# Set up the YouTube Data API client
DEVELOPER_KEY = 'AIzaSyDYi0hx3ReDAlCz3GXom7hyj8t0vvjWcKs'  # Replace with your YouTube API key
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)

# Specify the directory path to save the image
image_directory = os.path.join(os.getcwd(), 'static', 'images')

# Create the image directory if it doesn't exist
os.makedirs(image_directory, exist_ok=True)

def extract_video_id(url):
    query = urllib.parse.urlparse(url)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            p = urllib.parse.parse_qs(query.query)
            return p['v'][0]
        if query.path[:7] == '/embed/':
            return query.path.split('/')[2]
        if query.path[:3] == '/v/':
            return query.path.split('/')[2]
    raise ValueError('Invalid YouTube URL or unable to extract video ID.')


def get_comments(video_id):
    try:
        # Retrieve the comments for the specified video
        response = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            textFormat='plainText',
            maxResults=200,  # Adjust this value to retrieve more comments if needed
        ).execute()

        comments = []
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            comments.append(comment)

        return comments
    except HttpError as e:
        print(f'An error occurred: {e}')
        return []


def is_positive(comment):
    positive_words = ["good", "great", "excellent", "nice", "super", "fabulous", "smooth", "best", "love", "fantastic",
                      "wow", "amazing", "promising","fantabulous"]
    blob = TextBlob(comment)
    polarity = blob.sentiment.polarity
    return polarity > 0 and any(word in comment.lower() for word in positive_words)


def is_negative(comment):
    negative_words = ["bad", "poor", "terrible", "worst", "damage", "flop", "waste", "waste of money", "dont buy",
                      "horrible", "failure", "bullshit", "hell", "not available", "repair", "avoid", "cheap",
                      "issue", "never", "error", "scam","issue"]
    blob = TextBlob(comment)
    polarity = blob.sentiment.polarity
    return polarity < 0 and any(word in comment.lower() for word in negative_words)


def is_question(comment):
    question_words = ["how", "where", "what", "when", "?", "who"]
    return any(word.lower() in comment.lower() for word in question_words)


def save_comments(hashtag, comments):
    positive_comments = []
    negative_comments = []
    question_comments = []
    neutral_comments = []

    positive_words = ["good", "great", "excellent", "nice", "super", "fabulous", "smooth", "best", "love", "fantastic",
                      "wow", "amazing", "promising","Marvelous","Beautiful","Awesome",""]
    negative_words = ["bad", "poor", "terrible", "worst", "damage", "flop", "waste", "waste of money", "dont buy",
                      "horrible", "failure", "bullshit", "hell", "not available", "repair", "avoid", "cheap","Hate"
                      "issue", "never", "error", "scam","issue"]
    question_words = ["how", "where", "what", "when", "?", "who"]

    unique_comments = set()  # Store unique comments to remove duplicates

    for comment in comments:
        try:
            # Remove special characters from the comment using regular expressions
            comment = re.sub(r'[^\w\s]', '', comment)

            # Detect the language of the comment
            language = detect(comment)

            # Filter comments that are not in English
            if language != 'en':
                continue

            # Perform sentiment analysis
            blob = TextBlob(comment)
            polarity = blob.sentiment.polarity

            if polarity > 0 and any(word in comment.lower() for word in positive_words):
                positive_comments.append((comment, polarity))
            elif polarity < 0 and any(word in comment.lower() for word in negative_words):
                negative_comments.append((comment, polarity))
            elif any(word.lower() in comment.lower() for word in question_words):
                question_comments.append((comment, polarity))
            else:
                neutral_comments.append((comment, polarity))

            # Add comment to unique comments set
            unique_comments.add(comment)

        except LangDetectException:
            continue

    # Convert unique comments set back to a list
    unique_comments = list(unique_comments)

    # Sort the comments based on polarity
    positive_comments.sort(key=lambda x: x[1], reverse=True)
    negative_comments.sort(key=lambda x: x[1])
    neutral_comments.sort(key=lambda x: x[1])
    question_comments.sort(key=lambda x: x[1])

    filename_positive = f'{hashtag}_positive_comments.txt'
    filename_negative = f'{hashtag}_negative_comments.txt'
    filename_question = f'{hashtag}_question_comments.txt'
    filename_neutral = f'{hashtag}_neutral_comments.txt'

    with open(filename_positive, 'w', encoding='utf-8') as file:
        file.write('\n'.join([f'{comment[0]} (Polarity: {comment[1]})' for comment in positive_comments]))

    with open(filename_negative, 'w', encoding='utf-8') as file:
        file.write('\n'.join([f'{comment[0]} (Polarity: {comment[1]})' for comment in negative_comments]))

    with open(filename_question, 'w', encoding='utf-8') as file:
        file.write('\n'.join([f'{comment[0]} (Polarity: {comment[1]})' for comment in question_comments]))

    with open(filename_neutral, 'w', encoding='utf-8') as file:
        file.write('\n'.join([f'{comment[0]} (Polarity: {comment[1]})' for comment in neutral_comments]))

    print(f'Successfully saved {len(positive_comments)} positive comments to {filename_positive}.')
    print(f'Successfully saved {len(negative_comments)} negative comments to {filename_negative}.')
    print(f'Successfully saved {len(question_comments)} question comments to {filename_question}.')
    print(f'Successfully saved {len(neutral_comments)} neutral comments to {filename_neutral}.')


def generate_word_cloud(comments, hashtag):
    combined_comments = ' '.join(comments)
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(combined_comments)

    plt.figure(figsize=(10, 5))
    plt.title(f'Word Cloud for Hashtag: {hashtag}') 
    plt.imshow(wordcloud, interpolation='bilinear')

    # Save the plot as a PNG image
    filename = f'{hashtag}_Word_Cloud.png'
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(filename)
    print(f'Successfully saved the Word Cloud as {filename}.')
    plt.show()  # Display the word cloud


# Set up the Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = '737fde0f5e51686b2099cd6efa2b5c90b2ad359b78727152'  # Replace with a secret key

# Define the route for the home page
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_input = request.form['hashtag_or_link']

        if user_input.startswith('#'):
            hashtag = user_input[1:]
            session['hashtag'] = hashtag

            try:
                response = youtube.search().list(
                    part='id',
                    q=hashtag,
                    type='video',
                    maxResults=10,
                ).execute()

                video_ids = [item['id']['videoId'] for item in response['items']]
                all_comments = []

                for video_id in video_ids:
                    comments = get_comments(video_id)
                    all_comments.extend(comments)

                

                save_comments(hashtag, all_comments)
                generate_word_cloud(all_comments, hashtag)

                # Redirect to the results page after processing the input
                return redirect(url_for('results'))

            except HttpError as e:
                print(f'An error occurred: {e}')
        else:
            video_id = extract_video_id(user_input)
            if video_id:
                comments = get_comments(video_id)
                save_comments(video_id, comments)
                generate_word_cloud(comments, video_id)

                # Redirect to the results page after processing the input
                return redirect(url_for('results'))

    return render_template('index.html')  # Assuming you have an HTML template for the index




@app.route('/results')
def results():
    hashtag = session.get('hashtag')
    
    if not hashtag:
        return "Hashtag not found in session. Please go back and enter a hashtag."

    # Fetch the comments for the hashtag from YouTube or any other source
    # For demonstration, let's assume you fetch it from the same source as in the index route
    try:
        response = youtube.search().list(
            part='id',
            q=hashtag,
            type='video',
            maxResults=10,
        ).execute()

        video_ids = [item['id']['videoId'] for item in response['items']]
        all_comments = []

        for video_id in video_ids:
            comments = get_comments(video_id)
            all_comments.extend(comments)

    except HttpError as e:
        print(f'An error occurred: {e}')
        return "Error fetching comments."
    # Generate the word cloud image
    if all_comments:
        wordcloud = WordCloud().generate(' '.join(all_comments))
        image_stream = io.BytesIO()
        wordcloud.to_image().save(image_stream, format='PNG')
        image_stream.seek(0)
        word_cloud_url = url_for('static', filename=f'images/{hashtag}_Word_Cloud.png')
    else:
        word_cloud_url = None

    # Reading the saved comments from the text files
    filenames = {
        'positive': f'{hashtag}_positive_comments.txt',
        'negative': f'{hashtag}_negative_comments.txt',
        'question': f'{hashtag}_question_comments.txt',
        'neutral': f'{hashtag}_neutral_comments.txt'
    }

    saved_comments = {}
    for key, filename in filenames.items():
        with open(filename, 'r', encoding='utf-8') as file:
            saved_comments[key] = file.read().splitlines()

    wordcloud_filename = f'{hashtag}_Word_Cloud.png'
    word_cloud_url = url_for('static', filename=f'images/{wordcloud_filename}')
    word_cloud_download_url = url_for('download', filename=wordcloud_filename)

    return render_template('results1.html',
                           positive_comments_saved=saved_comments.get('positive', []),
                           negative_comments_saved=saved_comments.get('negative', []),
                           question_comments_saved=saved_comments.get('question', []),
                           neutral_comments_saved=saved_comments.get('neutral', []),
                           word_cloud_url=word_cloud_url,
                           word_cloud_download_url=word_cloud_download_url
                           )

@app.route('/download/<filename>')
def download(filename):
    directory = os.path.join(app.root_path, 'static', 'images')
    file_path = os.path.join(directory, filename)

    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "File not found."

if __name__ == '__main__':
    app.run(debug=True)
