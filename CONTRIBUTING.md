# Contributing
**This project welcomes collaboration from developers and site reliability engineers who want to help make Surge a powerful and practical tool. Please follow the code of conduct, have fun, and feel free to submit pull requests when you are ready to bring a new feature to life!**

## Working on an Issue
Find a current issue or create a new one if you have been invited to the repository. Assign the issue to yourself within GitHub to let others know you're working on it.

## Branch/Commit Naming Conventions
Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) for commit messages and branch names for clarity and consistency.

### Branches
Here are a couple of good branch names to use.
```
feature/[issue#]-short-description  # For new features (feat is also ok)
fix/[issue#]-short-description      # For bug fixes or smaller changes
chore/[issue#]-short-description    # For CI/CD
docs/[issue#]-short-description     # For documentation
```

### Commits
Commits should look similar to branch names. Try to keep your commit messages under 50 characters in length.

```
feat: short-description
fix: short-description
chore: short-description
```

1. Create your branch (`git checkout -b type/[issue#]-short-description`)
2. Commit your changes (`git commit -m "type: Added a great thing!"`)
3. Push to the branch (`git push origin type/[issue#]-short-description`)
4. Open a pull request on GitHub

##

**NOTE: When contributing, please be sure to lint and format your Python code to follow [PEP8 standards](https://peps.python.org/pep-0008/) to the best of your ability. Use the following commands in your terminal to spot linting errors and automatically format to adhere to the styling standards:**

Surges's automated checks will run when you open a pull request, but running them locally saves time and helps reviewers.

```
pytest -q --ruff  # Run tests and linter together
ruff check        # Lint codebase with Ruff
ruff format       # Auto format changes
```

##

**Once again, your contributions are much appreciated! Thanks for taking the time to follow best practices.**