from flask import Flask, render_template, request
import datetime
import smtplib
from constants import GMAIL_USER, GMAIL_PASSWORD

app = Flask(__name__)

thisYear = datetime.datetime.now().year

@app.route("/")
def home():
    return render_template("index.html", year=thisYear)

@app.route("/about")
def about():
    return render_template("about.html", year=thisYear)

@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        data = request.form
        name = data["name"]
        email = data["email"]
        phone = data["phone"]
        message = data["message"]
        # Gmail smtp stuff
        subject = "New Form from blog"
        email_text = """
        From: %s
        To: %s
        Subject: %s

        Phone: %s

        %s
        """ % (email, GMAIL_USER, subject, phone, message)
        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.ehlo()
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, GMAIL_USER, email_text)
            print("Email Sent!")
        except:
            print("Error connecting to server")
        return "<h1> Form Submitted </h1>"
    return render_template("contact.html", year=thisYear)

if __name__ == "__main__":
    app.run(debug=True)

