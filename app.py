
from flask import Flask, render_template, request, send_from_directory
import spacy
from summarizer.sbert import SBertSummarizer
import os
from difflib import SequenceMatcher
from rouge import Rouge
from flask_mail import Mail, Message

# Initialize SBERT Summarizer
sbert_model = SBertSummarizer('paraphrase-MiniLM-L6-v2')
nlp = spacy.load("en_core_web_sm")

app = Flask(__name__)

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Replace with your SMTP server address
app.config['MAIL_PORT'] = 587  # Replace with your SMTP server port (usually 587 for TLS)
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'k.vikaskumar986@gmail.com'  # Replace with your Gmail address
app.config['MAIL_PASSWORD'] = 'wtjpelitrptlzdbl'  # Replace with your Gmail password

mail = Mail(app)

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def calculate_accuracy(original_text, summary):
    rouge = Rouge()
    scores = rouge.get_scores(summary, original_text)
    rouge_l_score = scores[0]['rouge-l']['f']
    return rouge_l_score

def sbert_summarize(text, num_sentences=5):
    result = sbert_model(text, num_sentences=num_sentences)
    return result

def spacy_summarize(text, num_sentences=5):
    doc = nlp(text)
    ranked_sentences = sorted(doc.sents, key=lambda x: x.text.count('.') + x.text.count('!') + x.text.count('?'), reverse=True)
    result = ' '.join(sent.text for sent in ranked_sentences[:num_sentences])
    return result

@app.route('/static/<path:filename>')
def send_static(filename):
    return send_from_directory('static', filename)

@app.route("/")
def msg():
    return render_template('index.html')

@app.route("/summarize", methods=['POST', 'GET'])
def get_summary():
    if request.method == 'POST':
        if 'algorithm' in request.form:
            selected_algorithm = request.form['algorithm']
            if selected_algorithm == 'sbert':
                summary_function = sbert_summarize
            elif selected_algorithm == 'spacy':
                summary_function = spacy_summarize  # Use spaCy summarization
            else:
                return "Invalid algorithm selected."

            spacy_accuracy = sbert_accuracy = 0.0  # Initialize accuracy values

            if 'file' in request.files:
                uploaded_file = request.files['file']
                if uploaded_file.filename != '':
                    file_extension = uploaded_file.filename.split('.')[-1].lower()
                    if file_extension in ['jpg', 'png', 'jpeg', 'gif', 'raw']:
                        return "IMAGE FORMAT IS NOT SUPPORTED UPLOAD ONLY TEXTFILES OR DOCUMENTS."
                    if file_extension in ['pptx']:
                        return "PPT FORMAT IS NOT SUPPORTED UPLOAD ONLY TEXTFILES OR DOCUMENTS."

                    if not os.path.exists('uploads'):
                        os.makedirs('uploads')

                    temp_path = os.path.join('uploads', uploaded_file.filename)
                    uploaded_file.save(temp_path)

                    with open(temp_path, 'r') as file:
                        body = file.read()

                    original_word_count = len(body.split())

                    if original_word_count > 3000:
                        os.remove(temp_path)
                        return "WORD LIMIT UP TO 3000..."

                    result = summary_function(body)

                    summary_word_count = len(result.split())

                    spacy_accuracy = calculate_accuracy(body, result) if selected_algorithm == 'spacy' else 0.0
                    sbert_accuracy = calculate_accuracy(body, result) if selected_algorithm == 'sbert' else 0.0

                    os.remove(temp_path)

                    accuracy = calculate_accuracy(body, result)

                    # Pass the accuracy data to the template
                    accuracy_data = {
                        'spaCy': spacy_accuracy,
                        'SBERT': sbert_accuracy
                    }

                    return render_template('summary.html', original_text=body, original_word_count=original_word_count,
                                           summary_text=result, summary_word_count=summary_word_count, accuracy=f'{accuracy * 100:.2f}%',
                                           accuracy_data=accuracy_data)

            body = request.form['data']

            if len(body.split()) > 3000:
                return "WORD LIMIT UP TO 3000..."

            # Check if the input text contains non-English characters
            if not all(ord(char) < 128 for char in body):
                return "ENTER THE TEXT ONLY IN ENGLISH."

            result = summary_function(body)

            original_word_count = len(body.split())
            summary_word_count = len(result.split())

            spacy_accuracy = calculate_accuracy(body, result) if selected_algorithm == 'spacy' else 0.0
            sbert_accuracy = calculate_accuracy(body, result) if selected_algorithm == 'sbert' else 0.0

            accuracy = calculate_accuracy(body, result)

            # Pass the accuracy data to the template
            accuracy_data = {
                'spaCy': spacy_accuracy,
                'SBERT': sbert_accuracy
            }

            return render_template('summary.html', original_text=body, original_word_count=original_word_count,
                                   summary_text=result, summary_word_count=summary_word_count, accuracy=f'{accuracy * 100:.2f}%',
                                   accuracy_data=accuracy_data)

    return "Invalid request."

@app.route("/contact", methods=['GET'])
def contact():
    return render_template('contact.html')

@app.route("/send_message", methods=['POST'])
def send_message():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    subject = "Contact Form Submission"
    sender = email
    recipients = ["k.vikaskumar986@gmail.com"]
    message_body = f"Name: {name}\n"
    message_body += f"Email: {email}\n"
    message_body += f"Message: {message}\n"
    message = Message(subject=subject, sender=sender, recipients=recipients, body=message_body)
    try:
        mail.send(message)
        return "MESSAGE SENT SUCCESSFULLY!"
    except Exception as e:
        return f"Error sending email: {str(e)}"

if __name__ == "__main__":
    app.run(debug=True, port=8000)