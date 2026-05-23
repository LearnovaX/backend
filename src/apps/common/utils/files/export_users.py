from io import BytesIO
from urllib.parse import quote

import pandas as pd
from django.http import FileResponse, HttpResponse
from django.utils import timezone


def export_users_to_csv(data):
    df = pd.DataFrame(data)
    df = df.where(pd.notnull(df), None)
    filename = f"users-list-{timezone.now()}.csv"
    quoted_filename = quote(filename)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"; ' f"filename*=UTF-8''{quoted_filename}"
    )
    df.to_csv(path_or_buf=response, index=False, encoding="utf-8-sig")
    return response


def export_users_to_xlsx(data):
    output = BytesIO()
    df = pd.DataFrame(data)
    df = df.where(pd.notnull(df), None)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Users")
    output.seek(0)
    filename = f"users-list-{timezone.now()}.xlsx"
    quoted_filename = quote(filename)
    response = FileResponse(output, as_attachment=True, filename=filename)
    response["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    response["Content-Disposition"] = (
        f"attachment; " f"filename=\"{filename}\"; filename*=UTF-8''{quoted_filename}"
    )
    return response
