# Publish and transfer GuideBot with GitHub

No GitHub repository has been created or pushed by the assistant. This guide is for you to execute when you are ready to publish. The local project has a Git repository on `main`, with no commits, staged files, or remote.

## 1. Review the local files on Windows

```powershell
Set-Location 'D:\GuideBot humanoid campus information assistant'
git status --short --branch
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
git check-ignore .venv/Scripts/python.exe .tools/python/test.py .env logs/guidebot.log
```

The four paths in the last command should be printed as ignored. Do not add your virtual environment, downloaded Python runtime, logs, passwords, tokens, or private keys. Ignore rules prevent accidental additions of matching files; they do not detect every possible secret or remove files that were already tracked.

If starting from a copy that has no `.git` directory, initialize it once:

```powershell
git init -b main
```

## 2. Stage and inspect only the project files

These commands stage files locally; they do not upload anything:

```powershell
git add .gitattributes .gitignore README.md requirements.txt requirements-headless.txt run_guidebot.py guidebot tests docs
git status --short
git diff --cached --stat
git diff --cached
```

Inspect the staged diff before committing. If an unwanted file is staged before the first commit, remove it from the index while keeping the local file with `git rm --cached -- 'PATH_TO_FILE'`. Add an appropriate ignore rule before staging again. Do not use `git add -f` for private or generated files.

Create the first local commit after the review:

```powershell
git commit -m "Add GuideBot simulator and headless deployment mode"
```

If Git requests your author name and email, configure your own values locally for this repository. Do not copy another person's identity from an example.

```powershell
git config user.name 'YOUR_NAME'
git config user.email 'YOUR_EMAIL'
```

Replace both placeholders with your intended commit identity, then retry the commit.

## 3. Create an empty GitHub repository

Sign in to GitHub yourself, create a repository named `guidebot`, and choose its visibility. Leave GitHub's initial README, `.gitignore`, and license options unchecked for this first push because the local repository already contains project files. Choose a license separately when you decide the sharing terms.

## 4. Connect and push only when you choose to publish

Replace `YOUR_USERNAME` with the actual owner. This command configures the remote locally:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/guidebot.git
git remote -v
```

After confirming the remote points to the intended repository, publishing is the following explicit step:

```powershell
git push -u origin main
```

Complete GitHub authentication yourself when prompted. Never embed a token or password in the repository URL. The assistant will wait for your confirmation before executing a push or publishing a repository.

Reference: [GitHub's official local-code publishing instructions](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github).

## 5. Clone independently on the Orange Pi

On the board's own Armbian terminal, using its Ethernet connection:

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/guidebot.git guidebot
cd ~/guidebot
python3.13 -m guidebot --validate-data
python3.13 -m guidebot --headless
```

If you made the repository private, authenticate on the board separately using a supported GitHub HTTPS method. No laptop-to-board SSH or flash drive is involved. See [DEPLOYMENT.md](DEPLOYMENT.md) for optional setup, validation, and diagnostic commands.

## 6. Transfer later changes

On Windows, review changes, run tests, stage the intended files, commit, and push when approved:

```powershell
git status --short
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
git add guidebot tests docs README.md requirements.txt requirements-headless.txt .gitignore .gitattributes run_guidebot.py
git diff --cached
git commit -m "Describe the GuideBot changes"
git push
```

On the Orange Pi, stop GuideBot and pull:

```bash
cd ~/guidebot
git status --short
git pull --ff-only
python3.13 -m guidebot --validate-data
python3.13 -m guidebot --headless
```

Keep normal development on Windows and avoid independent edits on the deployment checkout where possible. If either checkout contains unexpected changes, review them before proceeding.
