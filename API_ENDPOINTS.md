# InvenTry API Endpoints Reference

Base URL: `http://localhost:8000` (or your deployed host)

All JSON request bodies should be sent with `Content-Type: application/json`.
Successful responses return JSON unless otherwise noted.
Error responses return JSON with `{"detail": "<error message>"}` and appropriate HTTP status code.

---

## 1. Root Endpoint

**GET /**  
**Description:** Simple health check endpoint returning a greeting message.  
**Authentication:** None  
**Request:** No parameters or body required.  
**Response:**  
- **200 OK**  
  Content-Type: `text/html`  
  Body: `<h1>Hello World!</h1>`  

---

## 2. User Registration

**POST /api/register**  
**Description:** Register a new user account.  
**Authentication:** None  
**Request Body:**  
```json
{
  "email": "string (email format)",
  "password": "string (plain text, will be hashed)",
  "first_name": "string",
  "last_name": "string"
}
```
**Constraints:**  
- `email` must be a valid email format and unique (not already registered).  
- `first_name` and `last_name` are required non-empty strings.  
- `password` should be strong (enforced by frontend; backend only hashes).  

**Responses:**  
- **201 Created**  
  ```json
  {
    "message": "User created successfully"
  }
  ```
- **400 Bad Request**  
  ```json
  {
    "detail": "Email already registered"
  }
  ```
- **500 Internal Server Error**  
  ```json
  {
    "detail": "<database or other error description>"
  }
  ```
**Notes:**  
- On success, the user is persisted with `role="user"` (default), `date_joined` set to current date, and `archived=false`.  
- Password is hashed using bcrypt before storage.

---

## 3. User Login

**POST /api/login**  
**Description:** Authenticate a user and set an HTTP-only cookie containing a JWT access token.  
**Authentication:** None (uses credentials in body)  
**Request Body:**  
```json
{
  "email": "string (email format)",
  "password": "string (plain text)"
}
```
**Responses:**  
- **200 OK**  
  ```json
  {
    "message": "Logged in successfully"
  }
  ```
  Additionally, sets an HTTP-only cookie:  
  - **Name:** `access_token`  
  - **Value:** `<JWT token>`  
  - **Attributes:** `HttpOnly; SameSite=Lax; Max-Age=86400` (24 hours)  
  - **Note:** `Secure` flag is currently `False` (set to `True` in production with HTTPS).  
- **401 Unauthorized**  
  ```json
  {
    "detail": "Incorrect email or password"
  }
  ```
  or  
  ```json
  {
    "detail": "Could not validate credentials"
  }
  ```
- **500 Internal Server Error**  
  ```json
  {
    "detail": "<database or other error description>"
  }
  ```
**Notes:**  
- The JWT token encodes the user ID (`sub`) and has a 1-hour expiration.  
- The cookie must be included in subsequent requests to authenticated endpoints (e.g., `/api/get_items`).  

---

## 4. Get Items

**GET /api/get_items**  
**Description:** Retrieve inventory items, optionally filtered by ID or category. Access to items is controlled by the logged-in user's role and item permissions (bitmask).  
**Authentication:** Required (valid JWT access token in `access_token` cookie)  
**Query Parameters:**  
- `id` (optional, string): If provided and `category` is not provided, returns the single item with this ID (if accessible).  
- `category` (optional, string): If provided and `id` is not provided, returns all items belonging to the category with this name.  
  - Special value `"all"` disables category filtering (returns all accessible items).  

**Constraints:**  
- Exactly one of `id` or `category` must be provided, unless `category` equals `"all"` (which acts as no filter).  
- Providing both `id` and `category` (when category ≠ `"all"`) results in a 400 error.  
- Providing neither results in a 400 error (unless `category` is `"all"`).  

**Responses:**  
- **200 OK**  
  Returns either a single item object or a list of item objects, depending on whether `id` was specified (and `category` not provided).  
  **Item Object Structure:**  
  ```json
  {
    "id": integer,
    "display_name": string (max 50 chars),
    "serial_number": string or null,
    "date_created": string (ISO date format, "YYYY-MM-DD"),
    "date_updated": string (ISO date format, "YYYY-MM-DD"),
    "category_id": integer,
    "assigned_to": integer or null,
    "permissions": string (4-character binary mask, e.g., "1100"),
    "archived": boolean,
    "date_archived": string or null (ISO date format)
  }
  ```
   - If `id` is provided and `category` is not provided: returns a single object (or 404 if not found).
  - Otherwise: returns a JSON array of item objects (may be empty).  

- **400 Bad Request**  
  ```json
  {
    "detail": "Bad Request"
  }
  ```
  Triggered by invalid query parameter combinations (see Constraints).  

- **401 Unauthorized**  
  ```json
  {
    "detail": "Could not validate credentials"
  }
  ```
  Missing or invalid access token cookie.  

- **404 Not Found**  
   ```json
   {
     "detail": "User corrupted, contact administrator"
   }
   ```  
   (Occurs if the user's role is not recognized; should not happen with valid data.)  
   Additionally, requesting a specific item by ID that doesn't exist or isn't accessible will return 404 with "Item not found".  
   Requesting a category by name that doesn't exist will return 404 with "Category not found".

- **500 Internal Server Error**  
  ```json
  {
    "detail": "<database or other error description>"
  }
  ```

**Permission Logic (Role-Based):**  
Let `perms` be the item's `permissions` CHAR(4) string (e.g., "1010").  
- **Admin role:** No permission check; can see all items (including archived?). The query does not filter by permissions or archived status.  
- **Moderator role:** Only items where `(perms & MOD_READ) != 0` (i.e., the first bit from left is 1). `MOD_READ` corresponds to binary `1000`.  
- **User role:** Only items where `(perms & USR_READ) != 0` (i.e., the third bit from left is 1). `USR_READ` corresponds to binary `0010`.  

**Additional Filtering:**  
- The endpoint does **not** filter by `archived` status; archived items are returned if permission checks pass.  
- No filtering on `assigned_to`, `date_created`, etc., besides the specified `id` or `category`.

---

## Notes for Frontend Development

1. **Authentication Flow:**  
   - After successful login, store the `access_token` cookie automatically (browser handles HttpOnly cookies).  
   - For subsequent requests to `/api/get_items`, ensure the cookie is sent (same-site lax; works for same-origin requests).  
   - If using a different domain or API gateway, you may need to forward the cookie or implement an auth header alternative (current design uses cookie only).

2. **Error Handling:**  
    - Always check HTTP status code; do not assume 200 means valid data.

3. **Data Types:**  
   - Dates are returned as strings in ISO 8601 format (`YYYY-MM-DD`). No time component.  
   - `serial_number` may be `null` if not set.  
   - `assigned_to` may be `null` if item is not assigned to any user.  
   - `permissions` is a 4-character string of `'0'` and `'1'` (e.g., `"0101"`).  

4. **Known Issues:**  
     - Cookie `Secure` flag is `False`; must be enabled for production HTTPS.

5. **Future Endpoints (Not Implemented):**  
   - POST /api/items (create item)  
   - PUT /api/items/{id} (update item)  
   - DELETE /api/items/{id} (delete item)  
   - Category management endpoints  
   - User profile/update endpoints  

--- 
*This document reflects the state of the code as of the latest commit. Always verify against the running backend if discrepancies are suspected.* 