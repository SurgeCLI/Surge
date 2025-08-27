# Surge · [![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE) [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)

### Development in Progress
Surge is an upcoming CLI tool for **real‑time system and network monitoring**, with planned support for **chaos engineering** and **stress testing**. It centralizes Linux tools like `curl`, `netstat`, `iostat`, `top`, and more into one clear interface with robust, actionable summaries and tabular/graphical output.

- **Declarative Monitoring:** Run simple, clear commands to get formatted, real‑time metrics for CPU, RAM, network, APIs, and more. Declarative output makes your monitoring predictable, easy to interpret, and actionable.
- **Component‑Like Commands:** Separate modules for system health, network tests, plotting graphs, and (future) load/chaos scenarios.
- **Learn Once, Run Anywhere:** Works in local, VPS, and production environments. Portable via Docker or direct CLI install.

## Roadmap
- [ ] Build a CLI interface that retrieves metrics on CPU, RAM, Disk/IO, and Network (Mostly Complete)
- [ ] Implement a suite of commands to test API endpoints
- [ ] Render simple, insightful graphs in the CLI
- [ ] Add a config file and scheduler for integration with CI/CD pipelines
- [x] ~~Dockerized deployment for easy setup~~
- [ ] Add an LLM integration for summaries via LangChain (Mostly Complete)
- [ ] (Future) Chaos engineering and stress testing capabilities
- [ ] (Future) Alerts, logging via email/SMS, continuous monitoring

## Installation
Currently, Surge is set to run via Docker, through the Python programming language. We plan to support direct CLI installs and publish to PyPI if the project gains traction.

### Clone the Repository

```
git clone https://github.com/SurgeCLI/Surge.git # HTTPS
git clone git@github.com:SurgeCLI/Surge.git     # SSH
```

### Set Up Docker
Install Docker Engine if you haven't already.
Once complete, run the following to build the image.

```
docker build -t surge:latest .
```

To run the container once, use the following command below with specified CLI arguments as needed.

```
docker run --rm surge:latest [command] [options]
```

### Set Up a Virtual Environment
If you prefer using a virtual environment to run the necessary dependencies, type in the following in your terminal:

```
python -m venv venv

source venv/bin/activate # Linux/Mac
.\venv\Scripts\activate  # Windows

pip install -r cli/requirements.txt
```

Be sure to use Linux with the installed packages found in the Dockerfile to avoid errors running subprocess commands locally.

## Examples and Documentation
More detailed documentation, demos, and visuals will be released with the MVP.

## Contributing
This repository is open for collaboration to build Surge as a tool for developers and site reliability engineers. Follow the code of conduct, have fun, and feel free to submit pull requests!

1. Create your Feature Branch (`git checkout -b feature/feature-name`)
2. Commit your Changes (`git commit -m "Added a great new feature!"`)
3. Push to the Branch (`git push origin feature/feature-name`)
4. Open a Pull Request on GitHub

**NOTE: When contributing, please be sure to lint and format your Python code to follow [PEP8 standards](https://peps.python.org/pep-0008/) to the best of your ability. Use the following commands in your terminal to spot linting errors and automatically format to adhere to the styling standards:**

```
ruff check
ruff format
```

## License
Surge is [MIT licensed](./LICENSE).