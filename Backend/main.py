from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

import os
import base64

import cloudinary
import cloudinary.api
import resend

# Load environment variables
load_dotenv()

print("===== RESEND CONFIG CHECK =====", flush=True)
print("RESEND_API_KEY exists:", bool(os.getenv("RESEND_API_KEY")), flush=True)
print("RESEND_API_KEY prefix:", os.getenv("RESEND_API_KEY", "")[:3], flush=True)
print("================================", flush=True)
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")

resend.api_key = RESEND_API_KEY

app = FastAPI(title="Photo Studio Booking API")

from fastapi.staticfiles import StaticFiles

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this after deployment
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/gallery/{folder:path}")
def get_gallery(folder: str = "photos"):

    media = []

    # Images
    images = cloudinary.api.resources(
        resource_type="image",
        type="upload",
        max_results=500
    )

    # Videos
    videos = cloudinary.api.resources(
        resource_type="video",
        type="upload",
        max_results=500
    )

    for result, media_type in [
        (images, "image"),
        (videos, "video")
    ]:

        for item in result["resources"]:

            asset_folder = item.get("asset_folder", "")

            if folder == "photos":
                if asset_folder.startswith("photos"):
                    media.append({
                        "id": item["public_id"],
                        "url": item["secure_url"],
                        "type": media_type
                    })

            elif asset_folder == folder:
                media.append({
                    "id": item["public_id"],
                    "url": item["secure_url"],
                    "type": media_type
                })

    return media

@app.get("/recent")
def get_recent_images():

    images_result = cloudinary.api.resources(
        resource_type="image",
        type="upload",
        max_results=100
    )

    videos_result = cloudinary.api.resources(
        resource_type="video",
        type="upload",
        max_results=100
    )

    media = []

    # Images
    for item in images_result["resources"]:
        asset_folder = item.get("asset_folder", "")
        if asset_folder.startswith("photos"):
            media.append({
                "id": item["public_id"],
                "url": item["secure_url"],
                "folder": asset_folder,
                "created_at": item["created_at"],
                "type": "image"
            })

    # Videos
    for item in videos_result["resources"]:
        asset_folder = item.get("asset_folder", "")
        if asset_folder.startswith("photos"):
            media.append({
                "id": item["public_id"],
                "url": item["secure_url"],
                "folder": asset_folder,
                "created_at": item["created_at"],
                "type": "video"
            })

    media.sort(
        key=lambda x: x["created_at"],
        reverse=True
    )

    return media[:10]

# ============================================================
# SEND EMAIL
# ============================================================

@app.post("/send-email")
async def send_email(
    to_email: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...)
):

    try:

        if not RESEND_API_KEY:
            raise RuntimeError("RESEND_API_KEY is not configured.")

        if not EMAIL_USER:
            raise RuntimeError("EMAIL_USER is not configured.")


        result = resend.Emails.send({
            "from": "Manu Photography <booking@manuphotography.co.in>",
            "to": [to_email],
            "subject": subject,
            "html": f"""
            <html>
            <body style="font-family:Arial;">

                <h2>{subject}</h2>

                <p>{message}</p>

                <hr>

                <p style="color:gray;">
                    MANU PHOTOGRAPHY
                </p>

            </body>
            </html>
            """
        })


        print("SEND-EMAIL RESULT:", result, flush=True)


        return {
            "success": True,
            "message": "Email sent successfully."
        }


    except Exception as e:

        print("SEND-EMAIL ERROR:", str(e), flush=True)

        return {
            "success": False,
            "message": str(e)
        }

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
        if not RESEND_API_KEY:
            raise RuntimeError("RESEND_API_KEY is not configured.")
        if not EMAIL_USER:
            raise RuntimeError("EMAIL_USER is not configured.")

        # ============================================================
        # 1. ADMIN EMAIL TEMPLATE
        # ============================================================
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
                📸 New Booking Request
            </h2>
            <hr>
            <h3>👤 Client Details</h3>
            <table style="width:100%;border-collapse:collapse;">
                <tr><td><b>Name</b></td><td>{fullName}</td></tr>
                <tr><td><b>Email</b></td><td>{email}</td></tr>
                <tr><td><b>Phone</b></td><td>{phone}</td></tr>
            </table>
            <hr>
            <h3>📅 Booking Details</h3>
            <table style="width:100%;border-collapse:collapse;">
                <tr><td><b>Photoshoot</b></td><td>{photoshootType}</td></tr>
                <tr><td><b>Date</b></td><td>{date}</td></tr>
                <tr><td><b>Time</b></td><td>{time}</td></tr>
                <tr><td><b>Location</b></td><td>{location if location else "Not Provided"}</td></tr>
                <tr><td><b>No. of People</b></td><td>{people if people else "Not Provided"}</td></tr>
            </table>
            <hr>
            <h3>📝 Additional Requirements</h3>
            <p>{requirements if requirements else "No additional requirements."}</p>
            <hr>
            <p style="color:gray;font-size:13px;">
                Booking request submitted from the Photo Studio Website.
            </p>
        </div>
        </body>
        </html>
        """

        # ============================================================
        # 2. ATTACHMENTS
        # ============================================================
        attachments = []
        if referenceImage is not None and referenceImage.filename:
            image_data = await referenceImage.read()
            encoded_file = base64.b64encode(image_data).decode("utf-8")
            attachments.append({
                "filename": referenceImage.filename,
                "content": encoded_file
            })

        # ============================================================
        # 3. SEND ADMIN EMAIL
        # ============================================================
        email_data = {
            "from": "Manu Photography <booking@manuphotography.co.in>",
            "to": [EMAIL_USER],
            "subject": f"📸 {photoshootType} Booking Request",
            "html": html
        }
        if attachments:
            email_data["attachments"] = attachments

        studio_result = resend.Emails.send(email_data)
        print("BOOKING EMAIL RESULT:", studio_result, flush=True)

        # ============================================================
        # 4. CUSTOMER EMAIL TEMPLATE
        # ============================================================
        customer_html = f"""
        <html>
        <body style="margin:0;padding:30px 15px;background:#f5f5f5;font-family:Arial,Helvetica,sans-serif;">
        <div style="max-width:650px;margin:auto;background:#ffffff;padding:35px;border-radius:12px;box-shadow:0 0 10px rgba(0,0,0,.15);">
            <div style="text-align:center;margin-bottom:25px;">
                <h2 style="color:#c58b2b;margin:0;font-size:24px;">📸 Booking Request Submitted Successfully</h2>
            </div>
            <hr style="border:none;border-top:1px solid #ddd;margin:20px 0;">
            <h3 style="margin-bottom:10px;color:#333;">Hi {fullName},</h3>
            <p style="color:#444;line-height:1.7;font-size:15px;">
                Thank you for choosing <b>MANU PHOTOGRAPHY</b>. We have successfully received your booking request.
            </p>
            <h3 style="color:#333;margin-top:28px;">📅 Booking Details</h3>
            <table style="width:100%;border-collapse:collapse;font-size:14px;">
                <tr><td style="padding:10px;border-bottom:1px solid #eee;"><b>📸 Photoshoot</b></td><td style="padding:10px;border-bottom:1px solid #eee;">{photoshootType}</td></tr>
                <tr><td style="padding:10px;border-bottom:1px solid #eee;"><b>📅 Date</b></td><td style="padding:10px;border-bottom:1px solid #eee;">{date}</td></tr>
                <tr><td style="padding:10px;border-bottom:1px solid #eee;"><b>🕐 Time</b></td><td style="padding:10px;border-bottom:1px solid #eee;">{time}</td></tr>
                <tr><td style="padding:10px;border-bottom:1px solid #eee;"><b>📍 Location</b></td><td style="padding:10px;border-bottom:1px solid #eee;">{location if location else "Not Provided"}</td></tr>
                <tr><td style="padding:10px;"><b>👥 No. of People</b></td><td style="padding:10px;">{people if people else "Not Provided"}</td></tr>
            </table>
            <hr style="border:none;border-top:1px solid #ddd;margin:25px 0;">
            <div style="background:#faf7f0;border-left:4px solid #c58b2b;padding:15px 18px;border-radius:6px;">
                <p style="margin:0;color:#444;line-height:1.7;font-size:14px;">
                    Your booking request has been received successfully. Our team will review your details and contact you shortly to confirm availability and finalize your booking.
                </p>
            </div>
            <h3 style="color:#333;margin-top:30px;">📞 Need Help?</h3>
            <p style="color:#444;line-height:1.7;font-size:14px;">If you have any questions or would like to make changes to your request, please contact us.</p>
            <table style="width:100%;border-collapse:collapse;margin-top:10px;">
                <tr><td style="padding:6px 0;color:#555;">📧 <b>Email</b></td><td style="padding:6px 0;">{EMAIL_USER}</td></tr>
                <tr><td style="padding:6px 0;color:#555;">📞 <b>Phone</b></td><td style="padding:6px 0;">{phone}</td></tr>
            </table>
            <hr style="border:none;border-top:1px solid #ddd;margin:28px 0 20px;">
            <div style="text-align:center;">
                <p style="margin:5px 0;color:#777;font-size:13px;">Capturing moments, creating memories.</p>
                <p style="margin:5px 0;font-weight:bold;color:#c58b2b;">MANU PHOTOGRAPHY</p>
            </div>
        </div>
        </body>
        </html>
        """

        # ============================================================
        # 5. SEND CUSTOMER EMAIL
        # ============================================================
        customer_email_data = {
            "from": "Manu Photography <booking@manuphotography.co.in>",
            "to": [email],
            "subject": "📸 Booking Request Submitted Successfully - Manu Photography",
            "html": customer_html
        }
        customer_result = resend.Emails.send(customer_email_data)
        print("CUSTOMER EMAIL RESULT:", customer_result, flush=True)

        return {"success": True, "message": "Booking request submitted successfully."}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "message": str(e)}
        
@app.get("/resend-debug")
def resend_debug():
    key = os.getenv("RESEND_API_KEY")

    return {
        "key_exists": bool(key),
        "key_prefix": key[:3] if key else None,
        "key_length": len(key) if key else 0
    }







