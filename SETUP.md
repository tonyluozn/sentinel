# Setup Guide

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -e .
   ```

2. **Set API keys** (see below)

3. **Run your first command**:
   ```bash
   sentinel fetch --repo owner/repo --milestone "v1.0.0"
   ```

## API Keys Configuration

### Option 1: Use .env File (Recommended)

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your actual keys:
   ```bash
   OPENAI_API_KEY=sk-your-actual-key-here
   GITHUB_TOKEN=ghp_your-actual-token-here
   ```

The `.env` file is automatically loaded when you import sentinel (requires `python-dotenv` which is included in dependencies).

**Note**: `.env` is in `.gitignore` so your keys won't be committed.

### Option 2: Environment Variables

### Required: OpenAI API Key

Sentinel uses OpenAI's API for the LLM agent. You **must** set this.

**Where to set it:**
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

**How to get it:**
1. Visit https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (it starts with `sk-`)
5. **Important**: Save it immediately - you won't see it again!

**Verify it's set:**
```bash
echo $OPENAI_API_KEY  # Should show your key (starts with sk-)
```

### Optional: GitHub Token

A GitHub token increases your API rate limit from 60/hour to 5,000/hour. **Highly recommended** if you'll be fetching data frequently.

**Where to set it:**
```bash
export GITHUB_TOKEN="ghp_your-token-here"
```

**How to get it:**
1. Visit https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name like "Sentinel"
4. Select scopes:
   - `public_repo` (for public repositories)
   - `repo` (if you need private repos)
5. Click "Generate token"
6. Copy the token (it starts with `ghp_`)

**Verify it's set:**
```bash
echo $GITHUB_TOKEN  # Should show your token (starts with ghp_)
```

## Making API Keys Persistent

### macOS / Linux (bash)

Add to `~/.bashrc` or `~/.zshrc`:
```bash
export OPENAI_API_KEY="sk-your-key-here"
export GITHUB_TOKEN="ghp_your-token-here"
```

Then reload:
```bash
source ~/.zshrc  # or source ~/.bashrc
```

### macOS / Linux (fish)

Add to `~/.config/fish/config.fish`:
```fish
set -gx OPENAI_API_KEY "sk-your-key-here"
set -gx GITHUB_TOKEN "ghp_your-token-here"
```

### Windows (PowerShell)

Add to your PowerShell profile:
```powershell
$env:OPENAI_API_KEY = "sk-your-key-here"
$env:GITHUB_TOKEN = "ghp_your-token-here"
```

Or set permanently:
```powershell
[System.Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'sk-your-key-here', 'User')
[System.Environment]::SetEnvironmentVariable('GITHUB_TOKEN', 'ghp_your-token-here', 'User')
```

## Troubleshooting

### "OPENAI_API_KEY environment variable not set"

**Solution**: Make sure you've exported the variable in your current shell:
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

### "Rate limit exceeded" (GitHub)

**Solution**: Set `GITHUB_TOKEN` to increase your rate limit:
```bash
export GITHUB_TOKEN="ghp_your-token-here"
```

### Keys not persisting after terminal restart

**Solution**: Add the export commands to your shell profile file (`~/.zshrc`, `~/.bashrc`, etc.)

## Security Notes

- **Never commit API keys to git** - they're in `.gitignore` for a reason
- **Don't share your keys** - they give access to your accounts
- **Rotate keys periodically** - especially if you suspect they're compromised
- **Use minimal scopes** - GitHub tokens should only have `public_repo` unless you need private repos
