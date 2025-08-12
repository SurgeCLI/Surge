# Surge · [![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE) [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)

### Development in Progress
Surge is an upcoming CLI tool for **real‑time system and network monitoring**, with planned support for **chaos engineering** and **stress testing**. It centralizes Linux tools like `curl`, `netstat`, `iostat`, `top`, and more into one clear interface with tabular and graphical output.

- **Declarative Monitoring:** Run simple, clear commands to get formatted, real‑time metrics for CPU, RAM, network, APIs, and more. Declarative output makes your monitoring predictable, easy to interpret, and actionable.
- **Component‑Like Commands:** Separate modules for system health, network tests, plotting graphs, and (future) load/chaos scenarios.
- **Learn Once, Run Anywhere:** Works in local, VPS, and production environments. Portable via Docker or direct CLI install.

## Roadmap
- Build a CLI interface that retrieves metrics on CPU, RAM, Disk/IO, and Network
- Implement a suite of commands to test API endpoints
- Render simple, insightful graphs in the CLI
- Add a config file and scheduler for integration with CI/CD pipelines
- Dockerized deployment for easy setup
- (Future) Chaos engineering and stress testing capabilities
- (Future) Alerts, logging via email/SMS, continuous monitoring

## Installation
Currently, Surge is set to run via Docker, through the Python programming language. We plan to support direct CLI installs and publish to PyPI if the project gains traction.

## Examples and Documentation
More detailed documentation, demos, and visuals will be released with the MVP.

## Contributing
This repository is open for collaboration to build Surge as a tool for developers and site reliability engineers. Follow the code of conduct, have fun, and feel free to submit pull requests!

1. Create your Feature Branch (`git checkout -b feature/feature-name`)
2. Commit your Changes (`git commit -m "Added a great new feature!"`)
3. Push to the Branch (`git push origin feature/feature-name`)
4. Open a Pull Request on GitHub

## License
Surge is [MIT licensed](./LICENSE).
