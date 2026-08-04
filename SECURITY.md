# Security Policy

## Reporting Security Vulnerabilities

Please **do not** report security vulnerabilities or exposed secrets through public GitHub issues.

Instead, please send a private security report to the repository owners or open a draft security advisory on GitHub.

## Security Practices

- **Zero Secret Commits**: Never commit actual API keys, database credentials, or `.env` files.
- **Path Traversal Guard**: All file storage mechanisms sanitize user-supplied filenames.
- **Untrusted Context Handling**: Prompt templates treat retrieved document content as untrusted user data to prevent prompt injection.
- **User Isolation**: Qdrant vector payload queries must always specify `user_id` filter conditions.
