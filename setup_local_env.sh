#!/bin/bash
# Quick setup script for local development

echo "Setting up local environment variables..."
echo ""
echo "Please provide your local PostgreSQL connection details:"
echo "Format: postgresql://username:password@localhost:5432/database_name"
echo ""
read -p "DATABASE_URL: " db_url

# Create .env file
cat > .env << ENVFILE
DATABASE_URL=$db_url
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
ENVFILE

echo ""
echo "✓ .env file created!"
echo "To use these variables, run: source .env (or export them manually)"
