# German-Study-Buddy
Automated German learning notes to validation to Hugo website pipeline.

---

# German Study Buddy

This project builds a small website for my German learning notes.
It runs automatically in the cloud.
I only need to upload a file to Google Drive, and the website updates by itself.

---

## How it works

1. I upload my daily `.md` file into a Google Drive folder called **Inbox**.
2. A small program in Google Apps Script reads that file.
3. The program sends the file to GitHub using a safe connection.
4. GitHub Actions runs my Python tools to:

   * check the file structure and tags,
   * split it into clean sections for the website,
   * build the Hugo site, and
   * publish it on GitHub Pages.
5. After the upload, the file moves to another Drive folder called **Processed**.

Everything happens automatically.
There is no need to download or upload anything by hand.

---

## What is inside the repository

* `tools/` – Python scripts that check and prepare the files
* `.github/workflows/site.yml` – The GitHub Actions file that runs the build
* `german-revision-helper/` – The Hugo site structure and layout files
* No `source/` or `content/` files are stored here.
  They are created only during each build in the cloud.

---

## Why this project

I wanted to keep my daily German notes simple, clean, and safe.
This setup lets me write freely in Markdown and see the results online without any extra work.
It also helps me keep my learning history organised.
