import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def dict2htmltable(data):
    """
    Convert a dictionary of customer names and invoices to an HTML table and save it to a file.

    Args:
        data (dict): A dictionary with keys 'customer' and 'invoice'.
    """
    # Extracting customer names and invoices
    cusname = data.get('customer', [])
    invoice = data.get('invoice', [])

    # Ensure that the length of both lists is the same
    if len(cusname) != len(invoice):
        raise ValueError("The length of 'customer' and 'invoice' lists must be the same.")

    # Create the HTML table
    html_content = "<h2 style='color:red; border:none;'>Order Confirmed</h2>"
    html_content += "<table border='1' style='border-collapse: collapse; width: 100%;'>"
    html_content += "<tr><th>Customer Name</th><th>Invoice</th></tr>"

    # Add rows for each customer and invoice
    for cus, inv in zip(cusname, invoice):
        html_content += f"<tr><td>{cus}</td><td>{inv}</td></tr>"

    html_content += "</table>"

    # Save the HTML content to a file
    with open("table.html", 'w') as f:
        f.write(html_content)

def send_mail(you):
    """
    Send an email with the HTML table as an attachment.

    Args:
        you (str): Recipient's email address.
    """
    me = "XXXXXhmbr12@gmail.com"
    msg = MIMEMultipart()
    msg['Subject'] = "Email confirmation"
    msg['From'] = me
    msg['To'] = you

    # Attach the HTML table as an email attachment
    try:
        with open("table.html", 'r') as f:
            attachment = MIMEText(f.read(), 'html')
            msg.attach(attachment)
    except FileNotFoundError:
       
        return

    # Setup the SMTP server connection
    username = 'XXXXXhmbr12'
    password = 'vksikttussvnbqef'
    s = smtplib.SMTP('smtp.gmail.com:587')

    try:
        s.starttls()
        s.login(username, password)
        s.sendmail(me, you, msg.as_string())
        s.quit()
        
    except Exception as e:
        print (f"Failed to send email: {str(e)}")

# Example usage
# if __name__ == "__main__":
#     data = {
#         'customer': ['Minhaj Enterprise', 'Minhaj Enterprise', 'Minhaj Enterprise'],
#         'invoice': ['T00791338830367', 'T00791338830367', 'T00791338830367']
#     }

#     dict2htmltable(data)  # Generate HTML table
#     send_mail("ithmbrbd@gmail.com")  # Send the email
