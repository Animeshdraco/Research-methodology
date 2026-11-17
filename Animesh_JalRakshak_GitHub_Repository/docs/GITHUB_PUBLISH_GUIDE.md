# Publish your individual GitHub repository

Each student must publish a separate personal repository. The main package is Nischal’s submission; the separately prepared Animesh package contains his personal dashboard and README. Neither remote repository has been created from this session. Follow your instructor's choice of public or private visibility. If the instructor requires public access for code/data inspection, choose Public.

## Create the empty repository

1. Sign in to GitHub and choose **New repository**.
2. Use a clear name such as `JalRakshak-Nischal` for Nischal or `JalRakshak-Animesh` for Animesh.
3. Choose the required visibility.
4. Do not initialise it with an extra README, licence or `.gitignore`; these files are already in this folder.
5. Create the repository and copy the HTTPS URL shown by GitHub.

## Push this folder from Windows

Open PowerShell or the VS Code terminal in the extracted `JalRakshak_Research_Repository` directory. Replace `<your-username>` with your actual GitHub username and use the exact repository name you created.

```powershell
git init
git add .
git commit -m "Add JalRakshak research project"
git branch -M main
git remote add origin https://github.com/<your-username>/JalRakshak-Research-Project.git
git push -u origin main
```

If Git asks you to sign in, complete GitHub's normal browser authentication. Do not paste a password, personal access token or SSH private key into project files or share it in chat.

After the push completes, open the repository page and check that `README.md`, `paper/`, `presentation/`, `dashboard/`, `analysis/`, `backend/`, `firmware/` and `docs/` are visible. The individual contribution statement and personal dashboard JPG are separate submission files and are intentionally not part of this repository package. Copy the real repository URL into the course submission form.
