# Notice

The component and platforms in this repository are not meant to be used by a
user, but as a "blueprint" that custom component developers can build
upon, to make more awesome stuff.

HAVE FUN! 😎

## Why?

This is simple, by having custom_components look (README + structure) the same
it is easier for developers to help each other and for users to start using them.

If you are a developer and you want to add things to this "blueprint" that you think more
developers will have use for, please open a PR to add it :)

## What?

This repository contains multiple files, here is a overview:

File | Purpose | Documentation
-- | -- | --
`.devcontainer.json` | Used for development/testing with Visual Studio Code. | [Documentation](https://code.visualstudio.com/docs/remote/containers)
`.github/ISSUE_TEMPLATE/*.yml` | Templates for the issue tracker | [Documentation](https://help.github.com/en/github/building-a-strong-community/configuring-issue-templates-for-your-repository)
`custom_components/ai_web_scraper/*` | Integration files, this is where everything happens. | [Documentation](https://developers.home-assistant.io/docs/creating_component_index)
`CONTRIBUTING.md` | Guidelines on how to contribute. | [Documentation](https://help.github.com/en/github/building-a-strong-community/setting-guidelines-for-repository-contributors)
`LICENSE` | The license file for the project. | [Documentation](https://help.github.com/en/github/creating-cloning-and-archiving-repositories/licensing-a-repository)
`README.md` | The file you are reading now, should contain info about the integration, installation and configuration instructions. | [Documentation](https://help.github.com/en/github/writing-on-github/basic-writing-and-formatting-syntax)
`requirements.txt` | Python packages used for development/lint/testing this integration. | [Documentation](https://pip.pypa.io/en/stable/user_guide/#requirements-files)

## How?

1. Create a new repository in GitHub, using this repository as a template by clicking the "Use this template" button in the GitHub UI.
1. Open your new repository in Visual Studio Code devcontainer (Preferably with the "`Dev Containers: Clone Repository in Named Container Volume...`" option).
1. Rename all instances of the `ai_web_scraper` to `custom_components/<your_integration_domain>` (e.g. `custom_components/awesome_integration`).
1. Rename all instances of the `AI Web Scraper` to `<Your Integration Name>` (e.g. `Awesome Integration`).
1. Run the `scripts/develop` to start HA and test out your new integration.

## AI Web Scraper Setup

After installing the integration and starting Home Assistant, configure the AI Web Scraper from the UI:

1. Go to **Settings > Devices & Services > Add Integration** and add **AI Web Scraper**.
1. Choose **Add AI Provider** to create a provider profile with:
   - Provider name
   - API key
   - Model name
   - Optional browserless URL
     - Use the browserless add-on HTTP endpoint, for example `http://browserless:3000`
     - If using the Home Assistant add-on, do not use `localhost` unless browserless is reachable from the Home Assistant instance.
     - Do not enter a WebSocket URL like `ws://...` or `wss://...`
1. After the provider exists, choose **Add Scraper Entry** and configure:
   - Scraper name
   - URL to scrape
   - Prompt text
   - Provider selection
   - Extraction mode (`Text/HTML Based Extraction` or `Browser Based Extraction`)
   - Interval seconds (`0` means manual-only refresh)
1. Once created, the integration exposes:
   - a data sensor for parsed scraper output
   - a refresh button to perform an immediate scrape
   - a status binary sensor for failure state

## Next steps

These are some next steps you may want to look into:
- Add tests to your integration, [`pytest-homeassistant-custom-component`](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component) can help you get started.
- Add brand images (logo/icon).
- Create your first release.
- Share your integration on the [Home Assistant Forum](https://community.home-assistant.io/).
- Submit your integration to [HACS](https://hacs.xyz/docs/publish/start).
