# Frontend Run Guide

This guide explains how to run the frontend (`index.html`) using a local static server.

## Prerequisites

- Node.js and npm installed

## Install `http-server`

```bash
npm install -g http-server
```

## Run the Frontend

From this folder:

```bash
cd /mosquito_survaillance_ai/WebApp/frontend
http-server
```

## Open in Browser

After running `http-server`, open the URL shown in your terminal (usually one of these):

- http://127.0.0.1:8080
- http://localhost:8080

Then load:

- `index.html` (served automatically as the default page)

## Stop the Server

Press `Ctrl + C` in the terminal.

## Notes

- If port `8080` is busy, run on a different port:

```bash
http-server -p 8081
```

- Backend setup commands can be added in a separate backend README when you share them.
