from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

import cloudinary
import cloudinary.api
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

# Load environment variables from this file's directory
base_dir = Path(__file__).resolve().parent
load_dotenv(base_dir / ".env")

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

app = FastAPI(title="Photo Studio Booking API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this after deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Photo Studio Booking API is running!"
    }


@app.get("/health")
def health():
    return {
        "status": "OK"
    }


@app.get("/gallery/{folder:path}")
def get_gallery(folder: str):
    folder = folder.strip("/")

    try:
        result = cloudinary.api.resources(
            type="upload",
            prefix=folder,
            max_results=100
        )
    except Exception as exc:
        return {
            "success": False,
            "message": f"Cloudinary gallery error: {exc}"
        }

    images = []
    for item in result.get("resources", []):
        if item.get("public_id", "").startswith(f"{folder}/") or item.get("asset_folder") == folder:
            images.append({
                "id": item["public_id"],
                "url": item.get("secure_url")
            })

    return images


@app.post("/booking")
async def booking(

    fullName: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    photoshootType: str = Form(...),
    date: str = Form(...),
    time: str = Form(...),
    location: str = Form(""),
    people: str = Form(""),
    requirements: str = Form(""),
    referenceImage: UploadFile = File(None)

):

    try:

        html = f"""
        <html>
        <body style="font-family:Arial;background:#f5f5f5;padding:30px;">

        <div style="
            max-width:650px;
            margin:auto;
            background:white;
            padding:30px;
            border-radius:12px;
            box-shadow:0 0 10px rgba(0,0,0,.15);
        ">

            <h2 style="color:#c58b2b;">
                 New Booking Request
            </h2>

            <hr>

            <h3>👤 Client Details</h3>

            <table style="width:100%;border-collapse:collapse;">

                <tr>
                    <td><b>Name</b></td>
                    <td>{fullName}</td>
                </tr>

                <tr>
                    <td><b>Email</b></td>
                    <td>{email}</td>
                </tr>

                <tr>
                    <td><b>Phone</b></td>
                    <td>{phone}</td>
                </tr>

            </table>

            <hr>

            <h3> Booking Details</h3>

            <table style="width:100%;border-collapse:collapse;">

                <tr>
                    <td><b>Photoshoot</b></td>
                    <td>{photoshootType}</td>
                </tr>

                <tr>
                    <td><b>Date</b></td>
                    <td>{date}</td>
                </tr>

                <tr>
                    <td><b>Time</b></td>
                    <td>{time}</td>
                </tr>

                <tr>
                    <td><b>Location</b></td>
                    <td>{location if location else "Not Provided"}</td>
                </tr>

                <tr>
                    <td><b>No. of People</b></td>
                    <td>{people if people else "Not Provided"}</td>
                </tr>

            </table>

            <hr>

            <h3>📝 Additional Requirements</h3>

            <p>
                {requirements if requirements else "No additional requirements."}
            </p>

            <hr>

            <p style="color:gray;font-size:13px;">
                Booking request submitted from the Photo Studio Website.
            </p>

        </div>

        </body>
        </html>
        """

        msg = EmailMessage()

        msg["Subject"] = f"📸 {photoshootType} Booking Request"

        msg["From"] = EMAIL_USER

        msg["To"] = EMAIL_USER

        msg.set_content("This email contains an HTML booking request.")

        msg.add_alternative(html, subtype="html")

        # Attach reference image if uploaded
        if referenceImage is not None and referenceImage.filename:

            image_data = await referenceImage.read()

            maintype, subtype = referenceImage.content_type.split("/")

            msg.add_attachment(
                image_data,
                maintype=maintype,
                subtype=subtype,
                filename=referenceImage.filename
            )

        # Send Email
        if not EMAIL_USER or not EMAIL_PASS:
            return {
                "success": False,
                "message": "Email credentials are not configured. Please set EMAIL_USER and EMAIL_PASS in .env."
            }

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)

        return {
            "success": True,
            "message": "Booking request sent successfully."
        }

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": "SMTP authentication failed. Verify your Gmail credentials and app password, and allow SMTP access if using Gmail."
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }