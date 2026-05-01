# 🔍 Giải thích kiến trúc & cơ chế hoạt động

> Tài liệu này giải thích **từng thành phần** của hệ thống, **luồng dữ liệu** giữa Frontend ↔ Backend ↔ Database, và **tại sao** mỗi phần lại được thiết kế như vậy.

---

## 1. Toàn cảnh hệ thống

```
Browser (localhost:3000)
  │
  │  HTTP Request (JSON + JWT Bearer Token)
  ▼
Next.js Frontend (React)
  │
  │  Axios call → http://localhost:8031
  ▼
FastAPI Backend (Python)
  ├── Auth Module ──────────────────► MongoDB (users collection)
  ├── RAG Pipeline                ▲
  │   ├── FAISS Vector DB ◄───────┘
  │   ├── Cross-Encoder Reranker
  │   └── OpenAI GPT-4o-mini
  └── History Module ──────────────► MongoDB (chat_logs collection)
```

---

## 2. Frontend (Next.js)

### 2.1 Cấu trúc thư mục frontend

```
frontend/
├── app/                    ← Next.js App Router (mỗi folder = 1 route)
│   ├── layout.tsx          ← Layout chung bao ngoài toàn bộ trang
│   ├── page.tsx            ← Trang chủ "/" (redirect sang /login)
│   ├── login/
│   │   └── page.tsx        ← Trang đăng nhập "/login"
│   ├── signup/
│   │   └── page.tsx        ← Trang đăng ký "/signup"
│   └── chat/
│       ├── page.tsx        ← Trang chat chính "/chat" (orchestrator)
│       ├── SideBar.tsx     ← Component sidebar + lịch sử chat
│       ├── MessageList.tsx ← Component hiển thị danh sách tin nhắn
│       └── ChatBox.tsx     ← Component ô nhập tin nhắn
└── lib/
    ├── auth.ts             ← Helpers: đọc token, parse JWT
    └── app.ts              ← Tất cả API calls đến backend
```

### 2.2 Luồng điều hướng (Routing)

```
Người dùng mở web
       │
       ▼
   "/" (page.tsx)
       │
       ├─ Có token trong localStorage? ──Yes──► "/chat"
       │
       └─ No ──► "/login"
                    │
                    ├─ Đăng nhập thành công ──► lưu token ──► "/chat"
                    │
                    └─ Chưa có tài khoản? ──► "/signup" ──► "/login"
```

### 2.3 Từng file frontend

#### `lib/auth.ts` – Quản lý token phía client
```typescript
// Lưu trữ JWT token trong localStorage của trình duyệt
// Không dùng cookie để tránh phức tạp về CSRF
getToken()    // Đọc token từ localStorage (safe với SSR)
parseJwt()    // Giải mã payload của JWT để đọc username, exp...
```

#### `lib/app.ts` – Cầu nối duy nhất với Backend API
```typescript
// Tạo một axios instance với baseURL = http://localhost:8031
// → Tất cả API call đều đi qua đây, không hardcode URL ở component

api.interceptors.response     // Tự động redirect về /login khi token hết hạn (401/403)

signup(username, password, confirmPassword)  // POST /auth/signup
login(username, password)                    // POST /auth/login  → trả access_token
queryRag(query, token)                       // POST /query       → trả answer + sources
getHistory(token)                            // GET  /history     → trả mảng chat logs
```

#### `app/login/page.tsx` – Trang đăng nhập
```
Render form username + password
    │
    ▼ handleLogin()
    │
    ├── gọi lib/app.ts → login(username, password)
    │       │
    │       ▼
    │   POST /auth/login → Backend → trả { access_token }
    │
    └── lưu token vào localStorage → router.push("/chat")
```

#### `app/signup/page.tsx` – Trang đăng ký
```
Render form username + password + confirm_password
    │
    ▼ handleSignup()
    │
    ├── kiểm tra password === confirmPassword (phía client)
    │
    ├── gọi lib/app.ts → signup(...)
    │       │
    │       ▼
    │   POST /auth/signup → Backend → tạo user trong MongoDB
    │
    └── router.push("/login")
```

#### `app/chat/page.tsx` – Trang chat (Orchestrator)
```
Đây là component "điều phối" – quản lý state và kết nối các component con

State:
  messages: Message[]   ← danh sách tin nhắn hiện tại trong session
  sidebarOpen: boolean  ← trạng thái mở/đóng sidebar

Khi mount:
  → kiểm tra token, nếu không có → redirect /login

handleSend(text):
  1. Thêm tin nhắn user vào messages
  2. Gọi queryRag(text, token)  ← POST /query
  3. Nhận response: { answer, sources, processing_time, used_k }
  4. Thêm tin nhắn assistant vào messages (kèm meta: sources, scores)

Render:
  <Sidebar />      ← hiển thị bên trái
  <MessageList />  ← hiển thị danh sách tin nhắn
  <ChatBox />      ← ô nhập liệu phía dưới
```

#### `app/chat/ChatBox.tsx` – Ô nhập tin nhắn
```
Input text + nút Gửi
    │
    ▼ onSubmit form
    │
    └── gọi prop onSend(text) → về page.tsx → handleSend()
```
> **Pattern**: ChatBox không biết gì về API. Nó chỉ nhận callback `onSend` từ cha.

#### `app/chat/MessageList.tsx` – Hiển thị tin nhắn
```
Nhận prop: messages: Message[]

Mỗi Message:
  - role = "user"      → hiển thị bong bóng xanh, căn phải
  - role = "assistant" → hiển thị bong bóng xám, căn trái
                         + meta block: processing_time, used_k
                         + danh sách sources:
                             - URL (link)
                             - rerank_score (màu xanh lá)
                             - similarity_score (màu xám)
                             - snippet (preview đoạn văn)
```

#### `app/chat/SideBar.tsx` – Lịch sử chat
```
Khi mount:
  → getHistory(token)  ← GET /history
  → setHistory(data)   ← lưu vào state

Render:
  - Nút toggle mở/đóng sidebar
  - Danh sách history: query + timestamp
  - Nút Help
  - Nút Logout → xóa token → /login
```

---

## 3. Backend (FastAPI)

### 3.1 Cấu trúc thư mục backend

```
backend/
├── main.py          ← Entry point: tạo app, đăng ký router, CORS, lifespan
├── auth.py          ← Route handler: /auth/signup, /auth/login
├── models.py        ← Pydantic schemas (validate request body)
├── database.py      ← Kết nối MongoDB
├── utils.py         ← Helpers: hash password, tạo/giải mã JWT
├── rag_cli.py       ← ⭐ Class RAGChatbot: toàn bộ pipeline RAG
├── auth_fol/
│   └── auth_bearer.py  ← Middleware kiểm tra JWT trên mỗi request
└── routes/
    ├── query.py     ← Route handler: POST /query
    └── history.py   ← Route handler: GET /history
```

### 3.2 `main.py` – Trái tim của ứng dụng

```python
# FastAPI khởi động theo luồng sau:

1. load_dotenv()             # đọc file .env vào os.environ

2. @asynccontextmanager      # lifespan = code chạy khi server start/stop
   async def lifespan():
       get_chatbot()         # khởi tạo RAGChatbot (load model, FAISS)
                             # → làm ấm server, tránh lần đầu query bị chậm
       yield                 # server chạy ở đây
                             # (code sau yield chạy khi server tắt)

3. CORS Middleware           # cho phép frontend localhost:3000 gọi API
                             # (browser chặn cross-origin nếu không có CORS)

4. include_router()          # đăng ký các router:
   - /auth  → auth.py
   - /query → routes/query.py
   - /history → routes/history.py
```

### 3.3 `database.py` – Kết nối MongoDB

```python
# MongoDB có 1 database "rag_project" chứa 2 collections:

db["users"]      ← lưu tài khoản: { username, password (hashed) }
db["chat_logs"]  ← lưu lịch sử:   { user, query, answer, sources,
                                      used_k, processing_time, timestamp }
```

### 3.4 `models.py` – Validation request

```python
# Pydantic tự động validate JSON body của request

class UserSignup:   username, password, confirm_password
class UserLogin:    username, password
class QueryRequest: query

# Nếu client gửi sai format → FastAPI tự trả 422 Unprocessable Entity
```

### 3.5 `utils.py` – Bảo mật

```python
# Mật khẩu:
hash_password(pw)           → bcrypt hash (không thể reverse)
verify_password(plain, hash) → so sánh an toàn

# JWT Token:
create_access_token({"sub": username})
  → tạo token có hạn 60 phút
  → ký bằng JWT_SECRET (chỉ server biết)

decode_jwt(token)
  → giải mã và xác thực chữ ký
  → trả payload hoặc None nếu invalid/hết hạn
```

### 3.6 `auth_fol/auth_bearer.py` – Middleware JWT

```python
# JWTBearer kế thừa HTTPBearer của FastAPI
# Được dùng như Dependency trong route:

@router.post("/query")
def query_rag(token: str = Depends(JWTBearer())):
    #                         ↑
    #   Trước khi vào hàm này, FastAPI tự gọi JWTBearer.__call__()
    #   → trích xuất token từ header "Authorization: Bearer <token>"
    #   → verify chữ ký JWT
    #   → nếu invalid → raise 403 ngay, không vào hàm
    #   → nếu valid → trả token string vào tham số

# Luồng xử lý request có JWT:
Request
  │ Header: Authorization: Bearer eyJhbG...
  ▼
JWTBearer.__call__()
  ├── Không có header → 403
  ├── scheme != "Bearer" → 403
  ├── JWT invalid/expired → 403
  └── OK → trả token → vào route handler
```

### 3.7 `auth.py` – Đăng ký / Đăng nhập

```python
POST /auth/signup
  1. Kiểm tra password == confirm_password
  2. Validate password (>=8 ký tự, có chữ/số/ký tự đặc biệt)
  3. Kiểm tra username đã tồn tại chưa (MongoDB)
  4. Hash password bằng bcrypt
  5. Lưu { username, hashed_password } vào MongoDB
  6. Trả { "msg": "User created successfully" }

POST /auth/login
  1. Tìm user trong MongoDB theo username
  2. verify_password(input, stored_hash)
  3. Nếu đúng → create_access_token({"sub": username})
  4. Trả { "access_token": "eyJhbG...", "token_type": "bearer" }
```

### 3.8 `routes/query.py` – RAG Endpoint

```python
POST /query  (protected by JWTBearer)

1. JWTBearer validate token → lấy được token string
2. decode_jwt(token) → lấy username từ payload["sub"]
3. rag_pipeline(query):
   a. get_chatbot()          → lấy singleton RAGChatbot
   b. chatbot.enhanced_search(query):
      - parse_search_params() → xác định k
      - retrieve_and_rerank() → FAISS + Cross-Encoder
      - combine_docs_chain()  → GPT-4o-mini generate
   c. format sources với scores
4. Lưu chat log vào MongoDB
5. Trả response JSON
```

### 3.9 `routes/history.py` – Lịch sử

```python
GET /history?limit=20&skip=0  (protected by JWTBearer)

1. Lấy username từ token
2. Query MongoDB: find({ user: username })
   .sort("timestamp", -1)   ← mới nhất trước
   .skip(skip).limit(limit) ← phân trang
3. Trả danh sách { query, answer, sources, timestamp, ... }
```

---

## 4. RAG Pipeline (`rag_cli.py`)

Đây là **trái tim của toàn bộ hệ thống AI**.

### 4.1 Class RAGChatbot – Khởi tạo

```python
RAGChatbot.__init__():
  _init_embeddings()   # load sentence-transformers (Bi-Encoder)
  _load_database()     # load FAISS index từ disk vào RAM
  _init_llm()          # tạo ChatOpenAI (GPT-4o-mini) client
  _init_prompt()       # PromptTemplate cho LLM
  _create_chains()     # tạo combine_docs_chain (LangChain)
  _init_reranker()     # load Cross-Encoder model
```

> Singleton pattern: chỉ khởi tạo 1 lần, tái sử dụng cho mọi request.

### 4.2 Luồng xử lý 1 query

```
Query: "Giá nhà tại Hà Nội tăng thế nào?"
  │
  ▼ [1] parse_search_params(query)
  │     → Phân tích cú pháp: "top 5 ...", "tìm 3 ...", "chi tiết", v.v.
  │     → Trả về (clean_query, k=3)
  │
  ▼ [2] retrieve_and_rerank(clean_query, k=3)
  │
  │   [2a] FAISS similarity_search_with_score(query, k=12)
  │        → Embed query → vector 384 chiều
  │        → IVF Index tìm 12 vector gần nhất (L2 distance)
  │        → Gắn similarity_score = 1/(1+distance) vào metadata
  │
  │   [2b] CrossEncoder.predict([(query, doc1), ..., (query, doc12)])
  │        → Model đọc cả query lẫn từng doc để tính score
  │        → Sort descending → giữ top-3
  │        → Gắn rerank_score vào metadata
  │
  ▼ [3] combine_docs_chain.invoke({input: query, context: top3_docs})
  │     → Format 3 docs thành chuỗi context
  │     → Ghép vào PromptTemplate:
  │         "Bạn là trợ lý... Ngữ cảnh: {context} Câu hỏi: {query}"
  │     → Gửi đến GPT-4o-mini qua OpenAI API
  │     → Nhận câu trả lời text
  │
  ▼ Trả về { answer, context: [doc1, doc2, doc3] }
```

### 4.3 Tại sao dùng 2 tầng retrieval?

```
Cách 1 – Chỉ FAISS (Bi-Encoder):
  • Embed query và doc RIÊNG LẼ → không hiểu ngữ cảnh lẫn nhau
  • Rất nhanh (milliseconds) nhưng kém chính xác
  • Giống: tìm từ khóa ngữ nghĩa gần nhau

Cách 2 – Thêm Cross-Encoder:
  • Đọc query VÀ doc CÙNG LÚC qua transformer attention
  • Hiểu được mối quan hệ query-doc sâu hơn
  • Chậm hơn (100-300ms) nhưng chính xác hơn nhiều
  • Giống: con người đọc câu hỏi và từng đoạn văn rồi chấm điểm

Chiến lược kết hợp (Retrieve → Rerank):
  FAISS lấy nhanh 12 ứng viên → Cross-Encoder chọn 3 tốt nhất
  → Tận dụng tốc độ của FAISS + độ chính xác của Cross-Encoder
```

---

## 5. Luồng dữ liệu đầy đủ – Từng kịch bản

### Kịch bản 1: Đăng nhập

```
[Browser]                    [Next.js]              [FastAPI]         [MongoDB]
   │                             │                      │                 │
   │──── nhập user/pass ────────►│                      │                 │
   │                             │──── POST /auth/login ►│                 │
   │                             │     {username,pass}  │                 │
   │                             │                      ├── find user ───►│
   │                             │                      │◄── {user doc} ──┤
   │                             │                      │                 │
   │                             │                      ├── verify bcrypt │
   │                             │                      ├── create JWT    │
   │                             │◄── {access_token} ───┤                 │
   │                             │                      │                 │
   │◄── lưu token localStorage ──┤                      │                 │
   │──── redirect /chat ────────►│                      │                 │
```

### Kịch bản 2: Gửi câu hỏi RAG

```
[Browser]         [Next.js]           [FastAPI]      [FAISS]  [CrossEncoder] [OpenAI]  [MongoDB]
   │                  │                   │              │           │           │          │
   │── nhập query ───►│                   │              │           │           │          │
   │                  │──POST /query ─────►│              │           │           │          │
   │                  │ Bearer <token>    │              │           │           │          │
   │                  │                   ├─JWTBearer    │           │           │          │
   │                  │                   ├─decode JWT   │           │           │          │
   │                  │                   │              │           │           │          │
   │                  │                   ├─embed query─►│           │           │          │
   │                  │                   │◄─12 docs ────┤           │           │          │
   │                  │                   │              │           │           │          │
   │                  │                   ├─rerank ───────────────►  │           │          │
   │                  │                   │◄─3 docs, scores ─────── ─┤           │          │
   │                  │                   │              │           │           │          │
   │                  │                   ├─generate answer ──────────────────► │          │
   │                  │                   │◄─ answer text ─────────────────────┤           │
   │                  │                   │              │           │           │          │
   │                  │                   ├─ save log ─────────────────────────────────────►│
   │                  │◄─{answer,sources}─┤              │           │           │          │
   │◄─ hiển thị ──────┤                   │              │           │           │          │
```

### Kịch bản 3: Xem lịch sử

```
[Browser]       [SideBar.tsx]      [lib/app.ts]      [FastAPI]        [MongoDB]
   │                │                   │                │                │
   │── mount ──────►│                   │                │                │
   │                │── getHistory() ──►│                │                │
   │                │                   │── GET /history ►│                │
   │                │                   │   Bearer token │                │
   │                │                   │                ├── find logs ──►│
   │                │                   │                │◄── [{...}] ────┤
   │                │                   │◄─{history:[]}──┤                │
   │                │◄─ extract array ──┤                │                │
   │◄── render list ┤                   │                │                │
```

---

## 6. Cơ chế bảo mật JWT

### JWT Token là gì?
```
eyJhbGciOiJIUzI1NiJ9  .  eyJzdWIiOiJhbGljZSIsImV4cCI6MTc0NjM3NjAwMH0  .  <signature>
        │                              │                                           │
   Header                         Payload                                     Chữ ký
 (algorithm)               (sub=username, exp=timestamp)               (ký bằng JWT_SECRET)
```

### Luồng xác thực
```
Client                              Server
  │                                    │
  │── POST /auth/login ───────────────►│
  │                                    ├── tạo JWT, ký bằng SECRET_KEY
  │◄── { access_token: "eyJ..." } ─────┤
  │                                    │
  │── POST /query ─────────────────────►│
  │   Authorization: Bearer eyJ...     │
  │                                    ├── JWTBearer trích xuất token
  │                                    ├── verify chữ ký với SECRET_KEY
  │                                    ├── kiểm tra exp (hết hạn?)
  │                                    ├── lấy username từ payload["sub"]
  │◄── { answer: "..." } ──────────────┤
```

> **Tại sao an toàn?** Token được ký bằng `JWT_SECRET` chỉ server biết.
> Bất kỳ ai cố sửa payload đều làm chữ ký sai → server từ chối.

---

## 7. CORS – Tại sao cần thiết?

```
Browser (localhost:3000) gọi API (localhost:8031)
    ↑
    └── Khác port = khác origin → Browser CHẶN mặc định (Same-Origin Policy)

Giải pháp: Backend thêm header:
  Access-Control-Allow-Origin: http://localhost:3000

FastAPI cấu hình trong main.py:
  allow_origins = ["http://localhost:3000"]
  allow_credentials = True   ← cho phép gửi cookies/auth headers
  allow_methods = ["*"]      ← GET, POST, PUT, DELETE...
  allow_headers = ["*"]      ← Authorization, Content-Type...
```

---

## 8. MongoDB – Cấu trúc dữ liệu

### Collection `users`
```json
{
  "_id": ObjectId("..."),
  "username": "alice",
  "password": "$2b$12$..."     ← bcrypt hash, KHÔNG lưu plaintext
}
```

### Collection `chat_logs`
```json
{
  "_id": ObjectId("..."),
  "user": "alice",
  "query": "Giá nhà Hà Nội tăng thế nào?",
  "answer": "Theo dữ liệu báo chí...",
  "sources": [
    {
      "doc_id": 1,
      "url": "https://dantri.com.vn/...",
      "section": "bat-dong-san",
      "similarity_score": 0.1012,
      "rerank_score": 3.927,
      "snippet": "Giá đất vùng ven..."
    }
  ],
  "used_k": 3,
  "processing_time": 2.41,
  "timestamp": ISODate("2026-05-01T10:30:00Z")
}
```

---

## 9. Tóm tắt luồng kết nối

| Layer | Technology | Nhiệm vụ |
|---|---|---|
| **Browser** | React (Next.js) | Render UI, quản lý state |
| **lib/app.ts** | Axios | HTTP client, intercept 401/403 |
| **FastAPI** | Python | Route handler, validate, orchestrate |
| **JWTBearer** | python-jose | Xác thực token trên mỗi request |
| **Pydantic Models** | Pydantic | Validate & type-check request body |
| **rag_cli.py** | LangChain + sentence-transformers | Pipeline AI: embed → retrieve → rerank → generate |
| **FAISS** | faiss-cpu | Vector database, tìm kiếm gần đúng (ANN) |
| **Cross-Encoder** | sentence-transformers | Rerank kết quả với độ chính xác cao |
| **OpenAI API** | gpt-4o-mini | Sinh câu trả lời tự nhiên từ context |
| **MongoDB** | pymongo | Lưu user accounts + chat history |

---

## 10. Điểm mấu chốt cần nhớ

1. **JWT không lưu trên server** – stateless. Server chỉ cần `JWT_SECRET` để verify.
2. **Token sống trong `localStorage`** – mỗi request phải đính kèm trong header `Authorization`.
3. **RAGChatbot là singleton** – load model 1 lần khi server start, dùng mãi.
4. **FAISS index đọc từ disk vào RAM** – tốc độ search ~12ms cho 360k vectors.
5. **Reranker chạy trên CPU** – ~200ms cho 12 docs, chấp nhận được cho demo.
6. **MongoDB `_id`** – tự sinh ObjectId, không cần truyền khi insert.
7. **`?? []` và `!= null`** – dùng thay `||` và `!== null` để xử lý cả `undefined`.

