import os
import base64
import django
from io import BytesIO

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cops.settings')
django.setup()

from django.conf import settings
from django.template.loader import render_to_string
from django.db.models import Sum
from datetime import date
from num2words import num2words
import qrcode
from weasyprint import HTML

from cps.models import CHImport, CHImportModelDetail, CHImportWarehouse, ChainsawBrand

REFERENCE_NO = '2026-05-18-PIC-36'

chimport = CHImport.objects.get(reference_no=REFERENCE_NO)

image_path = os.path.join(settings.BASE_DIR, 'crs', 'static', 'images', 'denr_header.png')
with open(image_path, 'rb') as f:
    logo_data_url = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

iso_path = os.path.join(settings.BASE_DIR, 'crs', 'static', 'images', 'iso.png')
with open(iso_path, 'rb') as f:
    iso_logo_url = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

red_filename = 'rednilo.png'
red_path = os.path.join(settings.BASE_DIR, 'crs', 'static', 'images', red_filename)
with open(red_path, 'rb') as f:
    red_logo_url = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

total_quantity = CHImportModelDetail.objects.filter(application_id=chimport.id).aggregate(
    total=Sum('quantity')
)['total'] or 0
quantity_in_words = num2words(total_quantity, to='cardinal', lang='en').capitalize()

brand = ChainsawBrand.objects.filter(id=chimport.brand_id).first()
brand_name = brand.name.upper() if brand else "N/A"

model_details = CHImportModelDetail.objects.filter(application_id=chimport.id)
warehouse_details = CHImportWarehouse.objects.filter(application_id=chimport.id)

date_approved = chimport.date_approved
date_expired = date_approved.replace(year=date_approved.year + 1) if date_approved else None

relative_url = f"/permit/{REFERENCE_NO}/checker/"
qr = qrcode.make(relative_url)
buffered = BytesIO()
qr.save(buffered, format="PNG")
qr_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

source_parts = []
if chimport.origin:
    source_parts.append(str(chimport.origin))
if chimport.supplier:
    source_parts.append(str(chimport.supplier))
if chimport.address:
    source_parts.append(str(chimport.address))
source = ' / '.join(source_parts) if source_parts else "N/A"

html_string = render_to_string('permit_pdf/permit_to_import.html', {
    'reference_no': chimport.reference_no or "",
    'estab_name': (chimport.estab_name.upper() if chimport.estab_name else ""),
    'estab_address': chimport.estab_address or "",
    'total_quantity': total_quantity,
    'quantity_in_words': quantity_in_words,
    'brand_name': brand_name,
    'model_details': model_details,
    'warehouse_details': warehouse_details,
    'source': source,
    'purpose': chimport.purpose or "",
    'date_approved': date_approved,
    'date_expired': date_expired,
    'logo_url': logo_data_url,
    'iso_url': iso_logo_url,
    "qr_code_base64": qr_b64,
    'red_logo_url': red_logo_url,
})

output_dir = os.path.join(settings.MEDIA_ROOT, 'chainsaw/pic')
os.makedirs(output_dir, exist_ok=True)
pdf_filename = f"DENR-NCR-{chimport.reference_no}.pdf"
pdf_path = os.path.join(output_dir, pdf_filename)
HTML(string=html_string).write_pdf(pdf_path)

print(f"Regenerated using {red_filename}: {pdf_path}")
