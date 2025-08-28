# Import necessary Python libraries and modules
from flask import Flask, request, render_template, flash, redirect, url_for
import os  # For working with file paths and directories
import re  # For cleaning strings (e.g., removing invalid characters)
import random  # For generating random numbers
from datetime import datetime  # For getting the current date
from PyPDF2 import PdfReader, PdfWriter  # For reading and writing PDF files
from reportlab.lib.pagesizes import A4  # For setting PDF page size
from reportlab.pdfgen import canvas  # For creating new PDF content
from reportlab.lib import colors  # For handling colors in PDFs (not used here but imported)
from io import BytesIO  # For handling in-memory binary data
import logging  # For logging errors and debug information

# Create a Flask application instance
app = Flask(__name__)

# Set a secret key for session management (required for flash messages)
# Replace 'your-secret-key' with a secure, unique string in production
app.secret_key = 'your-secret-key'

# Define directories for storing quotations and template files
# 'quotations' stores generated PDFs, 'files' stores the template PDF
app.config['QUOTATIONS_DIR'] = os.path.join(os.path.dirname(__file__), 'quotations')
app.config['TEMPLATE_DIR'] = os.path.join(os.path.dirname(__file__), 'files')

# Set up logging to track errors and debug information
# Logs will show detailed messages for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Function to generate a unique quotation number
def generate_quotation_number(output_dir):
    """
    Generates a unique quotation number like 'Q-001', 'Q-002', etc.
    Checks if the number already exists in the output directory to avoid conflicts.
    
    Args:
        output_dir (str): The directory where the PDF will be saved
    
    Returns:
        str: A unique quotation number (e.g., 'Q-123')
    """
    prefix = 'Q-'  # Prefix for the quotation number
    random_num = str(random.randint(1, 9999)).zfill(3)  # Generate a random 3-digit number (e.g., '123')
    quotation_no = f"{prefix}{random_num}"  # Combine prefix and number (e.g., 'Q-123')
    counter = 1  # Counter to avoid duplicate numbers
    
    # Check if a file with this quotation number already exists
    while os.path.exists(os.path.join(output_dir, f"{quotation_no}.pdf")):
        random_num = str(random.randint(1, 9999) + (counter * 10000)).zfill(3)  # Generate a new number
        quotation_no = f"{prefix}{random_num}"
        counter += 1  # Increment counter to try a new number if needed
    
    return quotation_no

# Function to search and retrieve quotation PDF files
def get_quotation_files(search_quotation_no='', search_rep=''):
    """
    Searches for PDF files in the quotations directory based on quotation number or representative name.
    
    Args:
        search_quotation_no (str): Optional quotation number to filter files (e.g., 'Q-123')
        search_rep (str): Optional representative name to filter directories
    
    Returns:
        dict: Contains either 'results' (list of files) or 'error' (error message)
    """
    base_dir = app.config['QUOTATIONS_DIR']  # Get the quotations directory
    results = []  # List to store found files
    
    # Check if the quotations directory exists
    if not os.path.isdir(base_dir):
        logger.error(f"Quotations directory not found: {base_dir}")
        return {'error': 'No quotations directory found.'}
    
    # Get a list of representative directories, optionally filtered by search_rep
    dirs = [
        d for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d))
        and (not search_rep or search_rep.lower() in d.lower())
    ]
    
    # If no directories are found, return an error
    if not dirs:
        error_msg = 'No representative directories found'
        if search_rep:
            error_msg += f' matching: Representative: {search_rep}'
        logger.error(f"No directories found in: {base_dir} for search: {search_rep}")
        return {'error': error_msg}
    
    # Define the file pattern to search for PDFs
    quotation_pattern = '*.pdf' if (not search_quotation_no and search_rep) else f'*{search_quotation_no}*.pdf'
    
    # Loop through each representative directory to find matching PDF files
    for dir_name in dirs:
        dir_path = os.path.join(base_dir, dir_name)
        # Find PDFs that match the search_quotation_no (case-insensitive)
        files = [f for f in os.listdir(dir_path) if f.endswith('.pdf') and search_quotation_no.lower() in f.lower()]
        
        # Add each file to the results list with its relative path
        for file in files:
            relative_path = os.path.join('quotations', dir_name, file)
            results.append({
                'file': file,
                'url': relative_path
            })
    
    # If no files are found, return an error
    if not results:
        error_msg = 'No quotations found'
        if search_rep or search_quotation_no:
            error_msg += ' matching: '
            error_msg += f'Representative: {search_rep}' if search_rep else ''
            error_msg += ' and ' if search_rep and search_quotation_no else ''
            error_msg += f'Quotation No: {search_quotation_no}' if search_quotation_no else ''
        logger.error(f"No files found for pattern: {base_dir}/*/{quotation_pattern}")
        return {'error': error_msg}
    
    return {'results': results}

# Function to create a PDF quotation using a template
def create_quotation_pdf(output_file, quotation_data, template_path):
    """
    Creates a PDF by overlaying quotation data onto a template PDF.
    
    Args:
        output_file (str): Path where the generated PDF will be saved
        quotation_data (dict): Data to populate the PDF (e.g., quotation_no, client_name, items)
        template_path (str): Path to the template PDF file
    
    Returns:
        bool or str: True if successful, error message if failed
    """
    try:
        # Load the template PDF
        template_pdf = PdfReader(template_path)
        output_pdf = PdfWriter()
        
        # Create a new PDF in memory to overlay text
        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=A4)
        
        # Define coordinates for placing text on the PDF (in points)
        coordinates = {
            'quotation_no': (540.27, 600.18),  # Top-right for quotation number
            'date': (540.27, 620.18),          # Top-right for date
            'rep': (545.27, 560.18),           # Top-right for representative name
            'client_name': (56.68, 575.18),    # Top-left for client name
            'items_start': (290, 450),         # Centered starting point for items table
            'subtotal': (540, 212.7),          # Bottom-right for subtotal
            'tax': (540, 178.53),              # Bottom-right for tax
            'total': (540, 145.36),            # Bottom-right for total
        }
        
        # Set the font for text
        c.setFont("Helvetica", 10)
        
        # Add quotation details to the PDF (right-aligned for top-right fields)
        c.drawRightString(coordinates['quotation_no'][0], coordinates['quotation_no'][1], quotation_data['quotation_no'])
        c.drawRightString(coordinates['date'][0], coordinates['date'][1], quotation_data['date'])
        c.drawRightString(coordinates['rep'][0], coordinates['rep'][1], quotation_data['rep'])
        c.drawString(coordinates['client_name'][0], coordinates['client_name'][1], quotation_data['client_name'])
        
        # Add items table (Quantity, Rate, Amount, VAT)
        y = coordinates['items_start'][1]  # Starting Y-coordinate for items
        row_height = 20  # Height of each row
        col_widths = [60, 60, 90, 80]  # Widths for Quantity, Rate, Amount, VAT columns
        
        # Draw each item row
        for item in quotation_data['quote_items']:
            x = coordinates['items_start'][0]  # Starting X-coordinate
            c.drawString(x, y, str(item['quantity']))  # Quantity
            x += col_widths[0]
            c.drawString(x, y, f"{item['rate']:.0f}")  # Rate (no decimals)
            x += col_widths[2]
            c.drawString(x, y, f"{item['amount']:.0f}")  # Amount (no decimals)
            x += col_widths[2]
            c.drawString(x, y, f"{item['vat']:.0f}")  # VAT (no decimals)
            y -= row_height  # Move up to the next row
        
        # Add totals (right-aligned)
        c.drawRightString(coordinates['subtotal'][0], coordinates['subtotal'][1], f"KES {quotation_data['subtotal']:.0f}")
        c.drawRightString(coordinates['tax'][0], coordinates['tax'][1], f"KES {quotation_data['tax']:.0f}")
        c.drawRightString(coordinates['total'][0], coordinates['total'][1], f"KES {quotation_data['total']:.0f}")
        
        # Finalize the overlay PDF
        c.showPage()
        c.save()
        
        # Merge the overlay with the template
        overlay_pdf = PdfReader(packet)
        for page_num in range(len(template_pdf.pages)):
            page = template_pdf.pages[page_num]
            if page_num < len(overlay_pdf.pages):
                page.merge_page(overlay_pdf.pages[page_num])
            output_pdf.add_page(page)
        
        # Save the final PDF to the output file
        with open(output_file, 'wb') as f:
            output_pdf.write(f)
        
        return True  # Success
    except Exception as e:
        logger.error(f"PDF generation failed: {str(e)}")
        return str(e)  # Return error message if something goes wrong

# Define the main route for the application
@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Handles the main page, including form submission and search functionality.
    
    Returns:
        Rendered HTML template with form data, search results, and messages
    """
    errors = []  # List to store error messages
    success = False  # Flag to indicate successful PDF generation
    success_message = ''  # Message to display on success
    search_errors = []  # List to store search-related errors
    # Initialize default quotation data
    quotation_data = {
        'quotation_no': '',
        'date': datetime.now().strftime('%Y-%m-%d'),  # Current date
        'client_name': '',
        'rep': '',
        'quote_items': [],
        'subtotal': 0,
        'tax': 0,
        'total': 0,
    }
    quotation_files = []  # List to store search results
    # Get search parameters from GET or POST requests
    search_quotation_no = request.args.get('search', '') if request.method == 'GET' else request.form.get('search_quotation_no', '')
    search_rep = request.args.get('search_rep', '') if request.method == 'GET' else request.form.get('search_rep', '')

    # Handle search for quotation files
    if search_quotation_no or search_rep:
        quotation_files_data = get_quotation_files(search_quotation_no, search_rep)
        if 'error' in quotation_files_data:
            search_errors.append(quotation_files_data['error'])
        else:
            quotation_files = quotation_files_data['results']
    else:
        # If no search parameters, get all quotation files
        quotation_files_data = get_quotation_files()
        if 'error' in quotation_files_data:
            search_errors.append(quotation_files_data['error'])
        else:
            quotation_files = quotation_files_data['results']

    # Handle form submission (POST request, not a search)
    if request.method == 'POST' and not (request.form.get('search_quotation_no') or request.form.get('search_rep')):
        # Retain form data for repopulation if there's an error
        quotation_data['client_name'] = request.form.get('client_name', '')
        quotation_data['rep'] = request.form.get('rep', '')
        
        # Get item data from the form (lists for multiple items)
        quantities = request.form.getlist('quantity[]')
        rates = request.form.getlist('rate[]')
        amounts = request.form.getlist('amount[]')
        vats = request.form.getlist('vat[]')
        
        # Create a safe directory name for the representative
        safe_rep_name = re.sub(r'[^A-Za-z0-9\-]', '_', quotation_data['rep'])
        safe_client_name = re.sub(r'[^A-Za-z0-9\-]', '_', quotation_data['client_name'])
        output_dir = os.path.join(app.config['QUOTATIONS_DIR'], safe_rep_name)
        
        # Create the output directory if it doesn't exist
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, mode=0o777)
            except OSError as e:
                errors.append(f'Failed to create directory: {output_dir}')
                logger.error(f"Failed to create directory: {output_dir}, error: {str(e)}")
        
        # Generate a unique quotation number
        quotation_data['quotation_no'] = generate_quotation_number(output_dir)
        
        # Initialize the items list
        quotation_data['quote_items'] = []
        
        # Validate that all item fields have the same number of entries
        if not (len(quantities) == len(rates) == len(amounts) == len(vats)):
            errors.append('Invalid item data submitted.')
        else:
            max_rows_per_page = 6  # Maximum rows per page (for PDF layout)
            if len(quantities) > max_rows_per_page * 10:
                errors.append(f'Too many items. Maximum {max_rows_per_page * 10} items allowed.')
            else:
                # Process each item
                for i in range(len(quantities)):
                    try:
                        quantity = float(quantities[i])
                        rate = float(rates[i])
                        amount = float(amounts[i])
                        vat = float(vats[i]) if vats[i] else 0
                    except ValueError:
                        errors.append(f'Incomplete item data at row {i + 1}. Quantity, rate, amount, and VAT are required.')
                        continue
                    
                    # Add valid item to the quotation data
                    if quantity and rate and amount:
                        quotation_data['quote_items'].append({
                            'quantity': quantity,
                            'rate': rate,
                            'amount': amount,
                            'vat': vat,
                        })
                        quotation_data['subtotal'] += amount
                        quotation_data['tax'] += amount * (vat / 100)
                    else:
                        errors.append(f'Incomplete item data at row {i + 1}. Quantity, rate, amount, and VAT are required.')
        
        # Calculate the total
        quotation_data['total'] = quotation_data['subtotal'] + quotation_data['tax']
        
        # Validate required fields
        if not quotation_data['client_name']:
            errors.append('Client name is required.')
        if not quotation_data['rep']:
            errors.append('Representative name is required.')
        if not quotation_data['quote_items']:
            errors.append('At least one complete item is required.')
        
        # Generate the PDF if there are no errors
        if not errors:
            try:
                output_file = os.path.join(output_dir, f"{quotation_data['quotation_no']}_{safe_client_name}.pdf")
                template_path = os.path.join(app.config['TEMPLATE_DIR'], 'QUOTATION.pdf')
                
                # Check if the template exists and the output directory is writable
                if not os.path.exists(template_path):
                    errors.append(f'Quotation template not found: {template_path}')
                elif not os.access(output_dir, os.W_OK):
                    errors.append(f'Output directory is not writable: {output_dir}')
                else:
                    # Generate the PDF
                    result = create_quotation_pdf(output_file, quotation_data, template_path)
                    if result is not True:
                        errors.append(f'PDF generation failed: {result}')
                    else:
                        success = True
                        success_message = f'Quotation generated successfully: {os.path.basename(output_file)}'
                        flash(success_message, 'success')
                        
                        # Refresh the quotation files list
                        quotation_files_data = get_quotation_files()
                        if 'error' in quotation_files_data:
                            search_errors.append(quotation_files_data['error'])
                        else:
                            quotation_files = quotation_files_data['results']
                        
                        # Redirect to the index page to show the updated list
                        return redirect(url_for('index'))
            except Exception as e:
                errors.append(f'PDF generation failed: {str(e)}')
                logger.error(f"PDF generation failed: {str(e)}")
    
    # Render the index.html template with all data
    return render_template('index.html', 
                         quotation_data=quotation_data,
                         quotation_files=quotation_files,
                         errors=errors,
                         success=success,
                         success_message=success_message,
                         search_errors=search_errors,
                         search_quotation_no=search_quotation_no,
                         search_rep=search_rep)

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)  # Run in debug mode for development
