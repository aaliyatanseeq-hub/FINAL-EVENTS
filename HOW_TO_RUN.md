# How to Run the Server

## ❌ WRONG Commands (Don't use these):
```powershell
uvicorn backend.pp:app --reload  # ❌ Wrong: 'backend' doesn't exist, and 'pp' is wrong
uvicorn Backend.app:app --reload  # ❌ May not work from root directory
```

## ✅ CORRECT Commands:

### Option 1: Run from Backend directory (RECOMMENDED)
```powershell
cd Backend
$env:PYTHONIOENCODING="utf-8"
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

### Option 2: Use the startup script
```powershell
cd Backend
.\start_server.ps1
```

### Option 3: Run from root directory
If you must run from root, use:
```powershell
$env:PYTHONIOENCODING="utf-8"
python -m uvicorn Backend.app:app --host 127.0.0.1 --port 8000 --reload
```

## Important Notes:
- Always use `app:app` (not `backend.pp:app` or `Backend.pp:app`)
- The file is `app.py` (not `pp.py`)
- Use `127.0.0.1` instead of `0.0.0.0` to avoid Windows permission issues
- Set `PYTHONIOENCODING=utf-8` to avoid Unicode errors

## Access the Server:
Once running, access at: `http://localhost:8000`

