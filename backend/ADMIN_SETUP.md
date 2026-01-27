# Admin Setup Instructions

## Setting Up the Admin User

Before running the application, you need to configure the admin credentials in the `.env` file.

### Step 1: Add Admin Credentials to `.env`

Open `backend/.env` and add the following lines:

```env
# Admin User Credentials
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=YourSecurePassword123!
```

**Important:**
- Replace `admin@yourdomain.com` with your desired admin email
- Replace `YourSecurePassword123!` with a strong, secure password
- Keep these credentials safe and never commit them to version control

### Step 2: Run the Admin Seed Script

After adding the credentials to `.env`, run the seed script to create the admin user:

```bash
cd backend
python scripts/seed_admin.py
```

You should see:
```
🔧 Running admin seed script...
✅ Admin user created successfully!
   Email: admin@yourdomain.com
   ID: <mongodb_object_id>
```

If the admin already exists, you'll see:
```
✅ Admin user already exists: admin@yourdomain.com
```

### Step 3: Login as Admin

1. Start the backend server: `python main.py`
2. Login with the admin credentials you configured
3. Navigate to Settings to configure API keys (OpenAI, Gemini)

## Role-Based Access

### Admin Role
- Can access all features including Settings
- Configures API keys for the entire system
- Full control over application settings

### User Role
- Cannot access Settings page
- Uses admin's configured API keys
- Can use Ingest and Compare features

## Troubleshooting

**Error: "ADMIN_EMAIL and ADMIN_PASSWORD must be set in .env file"**
- Make sure you've added both variables to your `.env` file
- Check for typos in the variable names

**Error: "MongoDB connection failed"**
- Ensure MongoDB is running
- Check your `MONGO_URI` in `.env`
