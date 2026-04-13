# 🔗 RAGNAROK — Hướng dẫn tích hợp API Upload Document

> **Context cho AI Frontend Developer**: Đây là tài liệu mô tả API backend cho luồng Upload Document qua S3 Presigned URL. Hãy đọc kỹ rồi implement phía frontend.

## Base URL

```
http://localhost:8080
```

> Swagger UI test: `http://localhost:8080/swagger-ui.html`

---

## Luồng Upload Document (3 bước)

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│ Bước 1   │         │ Bước 2   │         │ Bước 3   │
│ Lấy URL  │───▶     │ Upload   │───▶     │ Confirm  │
│ từ BE    │         │ lên S3   │         │ cho BE   │
└──────────┘         └──────────┘         └──────────┘
FE → BE API          FE → AWS S3          FE → BE API
```

---

## Bước 1: Lấy Presigned URL

### `GET /api/v1/documents/presigned-url`

| Param     | Type   | Required | Mô tả                    |
|-----------|--------|----------|--------------------------|
| `fileName`| string | ✅       | Tên file gốc, vd: `report.pdf` |

**Request:**
```
GET /api/v1/documents/presigned-url?fileName=report.pdf
```

**Response (200 OK):**
```json
{
  "presignedUrl": "https://ragnarok-bucket.s3.ap-southeast-1.amazonaws.com/abc-uuid/report.pdf?X-Amz-Algorithm=...",
  "fileKey": "abc-uuid/report.pdf"
}
```

| Field          | Type   | Mô tả                                           |
|----------------|--------|--------------------------------------------------|
| `presignedUrl` | string | URL dùng để PUT file trực tiếp lên S3 (hết hạn sau 15 phút) |
| `fileKey`      | string | Key định danh file trên S3, **cần lưu lại** để dùng ở Bước 3 |

---

## Bước 2: Upload file lên S3

Dùng `presignedUrl` từ Bước 1, gửi **PUT request** với file binary làm body.

**Request:**
```
PUT {presignedUrl}
Content-Type: application/octet-stream
Body: <file binary>
```

**Lưu ý quan trọng:**
- Method phải là **PUT** (không phải POST)
- **KHÔNG** gửi `Authorization` header — URL đã chứa signature
- `Content-Type` nên để `application/octet-stream` hoặc MIME type thực tế của file
- URL có hiệu lực **15 phút**, hết hạn thì phải lấy URL mới

**Response:** `200 OK` (empty body) = upload thành công.

### Code mẫu (JavaScript/TypeScript):

```typescript
// Bước 1: Lấy presigned URL
const res = await fetch(
  `${BASE_URL}/api/v1/documents/presigned-url?fileName=${encodeURIComponent(file.name)}`
);
const { presignedUrl, fileKey } = await res.json();

// Bước 2: Upload file trực tiếp lên S3
await fetch(presignedUrl, {
  method: "PUT",
  body: file,                              // File object từ <input type="file">
  headers: { "Content-Type": file.type },  // hoặc "application/octet-stream"
});
```

---

## Bước 3: Confirm Upload

Sau khi upload S3 thành công, gọi API confirm để backend trigger luồng AI xử lý file.

### `POST /api/v1/documents/confirm`

**Request:**
```
POST /api/v1/documents/confirm
Content-Type: application/json

{
  "fileKey": "abc-uuid/report.pdf"
}
```

| Field     | Type   | Required | Mô tả                              |
|-----------|--------|----------|-------------------------------------|
| `fileKey` | string | ✅       | Giá trị `fileKey` nhận từ Bước 1    |

**Response (200 OK):**
```json
{
  "status": "processing",
  "message": "File đã nhận, đang xử lý AI pipeline.",
  "fileKey": "abc-uuid/report.pdf"
}
```

> Backend sẽ bất đồng bộ gọi sang AI Service để xử lý file. FE nhận 200 OK ngay lập tức, **không cần chờ** AI xử lý xong.

---

## Full Flow Code Example (TypeScript)

```typescript
const BASE_URL = "http://localhost:8080";

async function uploadDocument(file: File): Promise<void> {
  // 1. Lấy presigned URL từ backend
  const urlRes = await fetch(
    `${BASE_URL}/api/v1/documents/presigned-url?fileName=${encodeURIComponent(file.name)}`
  );
  if (!urlRes.ok) throw new Error("Failed to get presigned URL");
  const { presignedUrl, fileKey } = await urlRes.json();

  // 2. Upload file trực tiếp lên S3 (PUT request)
  const uploadRes = await fetch(presignedUrl, {
    method: "PUT",
    body: file,
    headers: { "Content-Type": file.type || "application/octet-stream" },
  });
  if (!uploadRes.ok) throw new Error("Failed to upload to S3");

  // 3. Confirm upload → trigger AI pipeline
  const confirmRes = await fetch(`${BASE_URL}/api/v1/documents/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fileKey }),
  });
  if (!confirmRes.ok) throw new Error("Failed to confirm upload");

  const result = await confirmRes.json();
  console.log("Upload complete:", result);
  // result = { status: "processing", message: "...", fileKey: "..." }
}
```

---

## CORS

Backend đã mở CORS cho tất cả origins trên path `/api/**`:
- `allowedOrigins("*")`
- `allowedMethods("*")`
- `allowedHeaders("*")`

→ Frontend có thể gọi từ bất kỳ domain/port nào (localhost:3000, localhost:5173, v.v.)

---

## Error Handling gợi ý

| Tình huống                    | Cách xử lý                                  |
|-------------------------------|----------------------------------------------|
| Presigned URL hết hạn (403)   | Gọi lại Bước 1 để lấy URL mới               |
| Upload S3 thất bại            | Retry hoặc báo lỗi cho user                 |
| Confirm thất bại              | Retry POST confirm (file đã ở trên S3 rồi)  |
| File quá lớn                  | Backend cho phép tối đa **50MB**             |
