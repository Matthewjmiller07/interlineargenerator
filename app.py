import csv
import re
import requests
import subprocess
import os
from PyPDF2 import PdfReader
from flask import Flask, request, send_file

def escape_latex_special_chars(text):
    special_chars = {
        '&': '\\&', '%': '\\%', '$': '\\$', '#': '\\#', '_': '\\_', 
        '{': '\\{', '}': '\\}', '~': '\\textasciitilde{}', '^': '\\textasciicircum{}'
    }
    for char, escaped_char in special_chars.items():
        text = text.replace(char, escaped_char)
    return text

def remove_html_tags(text):
    text = re.sub(r'<span class=\"mam-spi-pe\">\{(פ|ס)\}</span>', r'{\1}', text)
    return re.sub('<.*?>', '', text)

def clean_hebrew(text):
    text = remove_html_tags(text)
    text = re.sub(r'(\{פ\}|\{ס\})', r' \1 ', text)
    return ''.join(re.findall('[\u0590-\u05FF\uFB1D-\uFB4F0-9 ]|\{פ\}|\{ס\}', text))

def get_hebrew_numeral(number):
    ones = ['', 'א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ז', 'ח', 'ט']
    tens = ['', 'י', 'כ', 'ל', 'מ', 'נ', 'ס', 'ע', 'פ', 'צ']
    hundreds = ['', 'ק', 'ר', 'ש', 'ת', 'תק', 'תר', 'תש', 'תת', 'תתק']
    
    special_cases = {15: 'טו', 16: 'טז'}
    if number in special_cases:
        return special_cases[number]
    elif number < 10:
        return ones[number]
    elif number < 100:
        return tens[number // 10] + ones[number % 10]
    elif number < 400:
        return hundreds[number // 100] + get_hebrew_numeral(number % 100)
    else:
        return 'תתק' + get_hebrew_numeral(number - 500)

def generate_latex_content(text_ref, hebrew_text, english_text, verse_numbers):
    latex_content = r'''\documentclass[10pt]{article}
\usepackage{fancybox}
\usepackage{fancyhdr}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{pgf}
\usepackage{tikz}
\usepackage{polyglossia}
\usepackage{bidi}
\usepackage{adjustbox}

\setdefaultlanguage{english}
\setotherlanguage{hebrew}

\newfontfamily\hebrewfont[Script=Hebrew, Path=./, Extension=.ttf]{TaameyFrankCLM-Medium}
\newfontfamily\englishfont[Path=./, Extension=.ttf]{Cardo-Regular}

\pagestyle{fancy}
\fancyhf{}  % Clear header and footer
\renewcommand{\headrulewidth}{0pt}  % No header line
\renewcommand{\footrulewidth}{0pt}  % No footer line
\fancyfoot[C]{''' + text_ref.replace("_", " ") + r'''}  

\begin{document}
\setlength{\parindent}{0pt}  % No indentation for new paragraphs
\begin{center}
\Large\textbf{''' + text_ref.replace("_", " ") + r'''}\\[1ex]
\end{center}

\newcommand{\decorativeseparator}{%
    \begin{center}
    $\ast$~$\ast$~$\ast$
    \end{center}
}

'''

    # Iterate over verses and their numbers
    previous_verse = 0
    chapter_number = 1
    for verse_number, hebrew_verse, english_verse in zip(verse_numbers, hebrew_text, english_text):
        # Check if a new chapter starts
        if verse_number < previous_verse:
            chapter_number += 1
            latex_content += f"\n\\section*{{Chapter {chapter_number}}}\n"

        # Update previous verse for next iteration
        previous_verse = verse_number

        # Add verse content
        hebrew_verse = clean_hebrew(remove_html_tags(hebrew_verse))
        hebrew_verse = escape_latex_special_chars(hebrew_verse)
        english_verse = remove_html_tags(english_verse)
        hebrew_numeral = get_hebrew_numeral(verse_number)

        latex_content += r'\begin{minipage}[t]{\textwidth}' + '\n'
        latex_content += r'\begin{adjustbox}{valign=t}'
        latex_content += r'\begin{minipage}[t]{.9\textwidth}'
        latex_content += r'\raggedleft\texthebrew{' + hebrew_verse + r'}'
        latex_content += r'\end{minipage}'
        latex_content += r'\begin{minipage}[t]{.1\textwidth}'
        latex_content += r'\hspace*{\fill}\fbox{\texthebrew{' + hebrew_numeral + r'}}\hspace{10pt}'
        latex_content += r'\end{minipage}'
        latex_content += r'\end{adjustbox}\par'
        latex_content += r'\vspace{5pt}'
        latex_content += r'\textbf{Verse ' + str(verse_number) + r':} ' + english_verse + r'\par'
        if verse_number < len(hebrew_text):
            latex_content += r'\decorativeseparator'
        latex_content += r'\vspace{10pt}'
        latex_content += r'\end{minipage}' + '\n'

    latex_content += r'\end{document}'

    return latex_content





def compile_latex_to_pdf(latex_content, output_filename):
    with open(output_filename + '.tex', 'w', encoding='utf-8') as file:
        file.write(latex_content)
    subprocess.run(['xelatex', output_filename + '.tex'], check=True)
    for ext in ['.aux', '.log', '.out', '.tex']:
        try: os.remove(output_filename + ext)
        except FileNotFoundError: pass


def create_pdfs_from_csv(csv_file_path, output_dir, start_row=1, end_row=929):
    chapters_info = []
    with open(csv_file_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)
        for i, row in enumerate(reader, start=1):
            if start_row <= i <= end_row:
                book, chapter = row[1:3]
                hebrew_text, english_text = fetch_interlinear_text(book, chapter)
                latex_content = generate_latex_content(book, chapter, hebrew_text, english_text)
                output_filename = f'{output_dir}/{book}_Chapter_{chapter}'
                compile_latex_to_pdf(latex_content, output_filename)
                chapters_info.append((book, chapter, f'{output_filename}.pdf'))
    return chapters_info

def create_pdf(book, chapter, output_dir):
    hebrew_text, english_text = fetch_interlinear_text(book, chapter)
    latex_content = generate_latex_content(book, chapter, hebrew_text, english_text)
    output_filename = f'{output_dir}/{book}_Chapter_{chapter}'
    compile_latex_to_pdf(latex_content, output_filename)
    print(f"PDF created for {book} Chapter {chapter}.")



app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return '''
    <html>
        <body>
            <form action="/generate_pdf" method="post">
                Text Reference: <input type="text" name="text_ref"><br>
                <input type="submit" value="Generate PDF">
            </form>
        </body>
    </html>
    '''


from io import BytesIO
import tempfile

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    text_ref = request.form['text_ref']

    try:
        hebrew_text, english_text, verse_numbers = fetch_interlinear_text(text_ref)
        latex_content = generate_latex_content(text_ref, hebrew_text, english_text, verse_numbers)

        # Use a temporary file to store the LaTeX file and compile it
        with tempfile.TemporaryDirectory() as tmpdirname:
            tex_file_path = os.path.join(tmpdirname, 'output.tex')
            with open(tex_file_path, 'w', encoding='utf-8') as tex_file:
                tex_file.write(latex_content)

            # Compile LaTeX file to PDF
            subprocess.run(['xelatex', tex_file_path, '-output-directory', tmpdirname], check=True)
            
            # Read the generated PDF into memory
            pdf_file_path = tex_file_path.replace('.tex', '.pdf')
            with open(pdf_file_path, 'rb') as pdf_file:
                pdf_in_memory = BytesIO(pdf_file.read())

        pdf_in_memory.seek(0)
        return send_file(pdf_in_memory, as_attachment=True, download_name=f"{text_ref.replace(' ', '_')}.pdf", mimetype='application/pdf')
    except Exception as e:
        return f"An error occurred: {e}"


import requests

def fetch_interlinear_text(text_ref):
    formatted_ref = format_text_ref_for_api(text_ref)
    base_url = f'https://www.sefaria.org/api/texts/{formatted_ref}?context=0&pad=0&commentary=0'

    # Fetch Hebrew text
    hebrew_response = requests.get(f'{base_url}&lang=he')
    if not hebrew_response.ok:
        return [], [], []
    hebrew_data = hebrew_response.json().get('he', [])

    # Try fetching English text with Koren translation
    english_response_koren = requests.get(f'{base_url}&lang=en&ven=The_Koren_Jerusalem_Bible')
    if english_response_koren.ok and english_response_koren.json().get('text'):
        english_data = english_response_koren.json().get('text', [])
    else:
        # Default to any available English translation
        english_response_default = requests.get(f'{base_url}&lang=en')
        if not english_response_default.ok:
            return [], [], []
        english_data = english_response_default.json().get('text', [])

    # Normalize and process text data
    start_verse = extract_start_verse(text_ref)
    hebrew_text, english_text, verse_numbers = process_text_data(hebrew_data, english_data, start_verse)

    return hebrew_text, english_text, verse_numbers

def process_text_data(hebrew_data, english_data, start_verse):
    # Initialize lists
    hebrew_text = []
    english_text = []
    verse_numbers = []

    verse_number = start_verse
    if isinstance(hebrew_data, list):
        for chapter_he, chapter_en in zip(hebrew_data, english_data):
            if isinstance(chapter_he, list):
                hebrew_text.extend(chapter_he)
                english_text.extend(chapter_en)
                verse_numbers.extend(range(verse_number, verse_number + len(chapter_he)))
                verse_number = 1  # Reset for next chapter
            else:
                hebrew_text.append(chapter_he)
                english_text.append(chapter_en)
                verse_numbers.append(verse_number)
                verse_number += 1
    else:
        hebrew_text.append(hebrew_data)
        english_text.append(english_data)
        verse_numbers.append(verse_number)

    return hebrew_text, english_text, verse_numbers

def format_text_ref_for_api(text_ref):
    # Format text reference for API request
    return text_ref.replace(" ", "_").replace(":", ".")

def extract_start_verse(text_ref):
    # Extract the starting verse from the text reference
    parts = text_ref.split()
    last_part = parts[-1]
    if ":" in last_part:
        chapter_verse = last_part.split("-")[0].split(":")
        if len(chapter_verse) == 2:
            verse = chapter_verse[1]
        else:
            # This case handles references without a chapter:verse format
            verse = 1
    else:
        # Default verse number to 1 if not specified
        verse = 1
    return int(verse)


# Example usage
hebrew_text, english_text, verse_numbers = fetch_interlinear_text("Mishnah Berachot 3:2-4:1")
for he, en, verse in zip(hebrew_text, english_text, verse_numbers):
    print(f'Verse {verse}:')
    print(f'Hebrew: {he}')
    print(f'English: {en}\n')


