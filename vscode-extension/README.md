# OmniForge Local — VS Code Extension Source

Experimental native VS Code extension providing commands for skill search, inspection, installation, and diagnostics. It calls the locally installed `omniforge` CLI, never a hosted service.

**Development:** Open this folder in VS Code and press F5 to launch an Extension Development Host. The extension is not published to VS Code Marketplace and a signed VSIX is not provided.

The extension requires a local OmniForge installation (`python -m pip install -e .` in the repository). Set `omniforge.executable` if `omniforge` is not available on PATH.

Use `OmniForge: Search Skills` or `OmniForge: Install Skill` from the Command Palette. Installation asks for confirmation and does not overwrite an existing skill directory.
