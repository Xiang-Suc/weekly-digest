# Automated Weekly Digest Workflow

This document outlines the automated system that generates and publishes the Weekly Digest every Monday.

## Overview

The system runs on **GitHub Actions** to automatically fetch activity data from GitHub and Trello, compile it into a Markdown report, and publish it to a Trello card.

## Visual Flow

```mermaid
graph TD
    Trigger([Trigger: Monday 09:00 UTC]) --> Runner{GitHub Runner}
    
    subgraph "Environment Setup"
        Runner --> Checkout[Checkout Code]
        Checkout --> SetupPy[Install Python 3.9]
        SetupPy --> InstallDeps[Install Dependencies]
    end
    
    InstallDeps --> Script[Run scripts/run_weekly_digest.py]
    
    subgraph "Data Collection (src/digest_core.py)"
        Script -->|Fetch Commits| GH[GitHub API]
        Script -->|Fetch Meeting Notes| TrelloRead[Trello API (Read)]
        Script -->|Fetch Board Actions| TrelloRead
    end
    
    subgraph "Processing"
        GH & TrelloRead --> Generate[Generate Markdown Report]
    end
    
    subgraph "Publication"
        Generate -->|Create Card| TrelloWrite[Trello API (Write)]
        Generate -->|Attach .md File| TrelloWrite
    end
    
    TrelloWrite --> Result([New Trello Card in Inbox])
```

## Detailed Process

### 1. Trigger

- **Schedule**: The workflow is triggered automatically by a cron job set to `0 9 * * 1` (Every Monday at 09:00 UTC).
- **Manual**: It can also be triggered manually via the "Run workflow" button in the GitHub Actions tab.

### 2. Environment Setup

The workflow spins up an `ubuntu-latest` virtual machine and performs the following steps:

1. **Checkout**: Downloads the latest code from the repository.
2. **Python Setup**: Installs Python 3.9.
3. **Dependencies**: Installs required libraries (`requests`, `Flask`) from `requirements.txt`.

### 3. Execution & Data Collection

The main script `scripts/run_weekly_digest.py` executes and orchestrates the data fetching:

- **Date Calculation**: Determines the date range for the previous week (Monday to Sunday).
- **GitHub Data**: Fetches commits from the `zcashme` organization and specific repositories like `ZcashUsersGroup/zcashme`.
- **Trello Data**:
  - Fetches cards from the "Meeting Notes" list.
  - Fetches "In Progress" and "Completed" actions from the board.

### 4. Report Generation

The collected data is formatted into a structured Markdown string:

- **Transcripts Summary**: Bullet points of meeting notes.
- **GitHub Commits**: Grouped by repository and branch.
- **Trello Activity**: Grouped by column ("In Progress", "Completed") and card.

### 5. Publication

The script interacts with the Trello API to publish the result:

1. **Find Target**: Locates the target list (defined by `TRELLO_TARGET_LIST_ID` or searches for "Inbox").
2. **Create Card**: Creates a new card titled "Weekly Digest: [Start Date] - [End Date]".
3. **Attach Report**: Uploads the full generated Markdown content as a file attachment (`.md`) to the card for archiving and easy reading.

## Configuration

For this workflow to function, the following **Secrets** must be configured in the GitHub Repository settings:

| Secret Name | Description |
| :--- | :--- |
| `TRELLO_KEY` | Your Trello API Key. |
| `TRELLO_TOKEN` | Your Trello API Token. |
| `TRELLO_TARGET_LIST_ID` | (Optional) ID of the list where the card should be created. |
| `GITHUB_TOKEN` | (Auto-provided) Used to fetch GitHub data. |
