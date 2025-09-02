"""
AI Monitoring Module
Collects metrics -> Analyze -> Suggest Fixes -> Execute with confirmation (ideally)
"""

import json
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from dotenv import load_dotenv
import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import SystemMessage, HumanMessage
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


class DataFormat(Enum):
    """
    Experiment with different data formats to find out what works best

    Three data formats:
        RAW: raw data contents
        STRUCTURED: parsed into json formats
        HYBRID: both of them

    """

    RAW = "raw"
    STRUCTURED = "structured"
    HYBRID = "hybrid"


class Verbosity(Enum):
    """
    AI output detail level

    Having three level:
        CONCISE: just the essentials
        NORMAL: balanced detail
        DETAILED: full analysis
    """

    CONCISE = "concise"
    NORMAL = "normal"
    DETAILED = "detailed"


@dataclass
class SystemSnapshot:
    """
    Data structure for system state

    Usage:
    This will be used for storing the data snapshot from our monitor such as:
    load average
    cpu cores
    memory db
    disk usage
    """

    load_avg: List[float]
    cpu_cores: int
    memory_db: Dict[str, int]
    disk_usage_percent: float

    # raw outputs for experimentation
    raw_uptime: Optional[str] = None
    raw_free: Optional[str] = None
    raw_df: Optional[str] = None
    raw_top: Optional[str] = None

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


class MetricCollector:
    """
    Metric collection from shell commands

    Usage:
    It will run some simple shell commands and we'll take that output
    then store it in a snap shot and use it for our AI to analyze
    """

    @staticmethod
    def run_cmd(cmd: str) -> str:
        """Execute shell commands and return stripped output"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=5
            )

            return result.stdout.strip()
        except Exception:
            # When testing I'll see what exactly the error is then isolate it with correct error exceptons
            pass

    def collect(self, include_raw: bool = False) -> SystemSnapshot:
        """Collecting current system metrics"""

        # getting the strcutured data
        uptime_raw = self.run_cmd("uptime")
        # using awk to pattern search for 'average' and output the value $2
        load_str = self.run_cmd("uptime | awk -F'average:' '{print $2}'")
        load_avg = [float(x.strip(",")) for x in load_str.split()]

        # Number of cpu cores
        cores = int(self.run_cmd("nproc"))
        # memory information
        mem_info = self.run_cmd("free -m | grep Mem").split()
        memory = {
            "total": int(mem_info[1]),
            "used": int(mem_info[2]),
            "free": int(mem_info[3]),
        }

        # disk information
        disk_info = self.run_cmd("df -h / | tail -1").split()
        disk_percent = float(disk_info[4].strip("%"))

        # create the snapshot
        snapshot = SystemSnapshot(
            load_avg=load_avg,
            cpu_cores=cores,
            memory_db=memory,
            disk_usage_percent=disk_percent,
        )

        # if we want to check out the raw output we can just set that to true when calling it
        if include_raw:
            snapshot.raw_uptime = uptime_raw
            snapshot.raw_free = self.run_cmd("free -m")
            snapshot.raw_df = self.run_cmd("df -h")
            snapshot.raw_top = self.run_cmd("top -bn1 | head -20")

        # otherwise we'll just return the snapshot we got
        return snapshot


class CommandExecutor:
    """
    Command execution with confirmation by users

    Usage:
    Uses for actionable fixes determine by the LLM
    User can then determine if they want to use such commands to allow fix
    """

    FIX_COMMANDS = [
        "systemctl restart",
        "systemctl stop",
        "kill",
        "nice",
        "renice",
        "sync",
        # found this on stack overflow: clear caches
        "echo 3 > /proc/sys/vm/drop_caches",
    ]

    DIAGNOSTICS_COMMANDS = [
        "systemctl status",
        "journalctl",
        "ps aux",
        "netstat",
        "free",
        "lsof",
        "df",
        "top -bn1",
    ]

    def __init__(self, console: Console):
        self.console = console

    def is_diagnostic_command(self, command: str) -> bool:
        """Checking if the command is part of what we have in the diagnostics commands"""
        return any(cmd in command for cmd in self.DIAGNOSTICS_COMMANDS)

    def execute(self, command: str, require_confirm: bool = True) -> Tuple[bool, str]:
        """
        Execution of the command from LLM with user confirmation

        Usage:
            LLM will analyze our metrics and come up with some sort of solution that allows actionable cmds
            Thus user can check the command and confirm with LLM to give consent to action those cmds
        """

        if not self.is_diagnostic_command(command):
            if require_confirm:
                self.console.print(f"[yellow]Command: {command}[/yellow]")
                if not Confirm.ask("Execute this fix?"):
                    return False, "Cancelled by user"

        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )

            return result.returncode == 0, result.stdout

        except Exception as err:
            return False, str("Error is: ", err)


class AIMonitor:
    """
    Main part of the execution for the AI analysis
    """

    # we will need to tweak the prompt based on the output, maybe we'll create like a ranking system to value which kind
    # of the output we'd like to display

    SYSTEM_PROMPT = """
    You are a DevOps expert analyzing system metrics.

    Your job:
        1. Analyze the provided system state
        2. Identify any issues or optimization opportunities
        3. Suggest specific, actionable fixes

    Be CONCISE and ACTIONABLE. Format your response as:
    SUMMARY: One sentence system status
    ISSUES: Bullet points of problems (if theres any)
    ACTIONS: Specific commands to fix issues (if theres any)
    
    ONLY suggest fixes if there are actual problems.
    """

    def __init__(
        self,
        data_format: DataFormat = DataFormat.HYBRID,
        verbosity: Verbosity = Verbosity.NORMAL,
        memory_window: int = 3,
    ):
        self.console = Console()
        self.data_format = data_format
        self.verbosity = verbosity

        # calling in the LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", google_api_key=GEMINI_API_KEY, temperature=0.1
        )

        # memory for context
        self.memory = ConversationBufferWindowMemory(
            k=memory_window,
            return_messages=True,
        )

        self.collector = MetricCollector()
        self.executor = CommandExecutor(self.console)

    def _prepare_data(self, snapshot: SystemSnapshot) -> str:
        """Prepare data based on format setting"""

        if self.data_format == DataFormat.RAW:
            return f"""
            Raw outputs:
            uptime: {snapshot.raw_uptime}
            free: {snapshot.raw_free}
            df: {snapshot.raw_df}
            """
        elif self.data_format == DataFormat.STRUCTURED:
            # Sending structure data with json
            data = {
                "load_avg": snapshot.load_avg,
                "cores": snapshot.cpu_cores,
                "load_per_core": [
                    load / snapshot.cpu_cores for load in snapshot.load_avg
                ],
                "memory": snapshot.memory_db,
                "memory_usage_percent": (
                    snapshot.memory_db["used"] / snapshot.memory_db["total"]
                )
                * 100,
                "disk_usage_percent": snapshot.disk_usage_percent,
            }

            return f"System Metrics:\n{json.dumps(data, indent=2)}"

        else:
            structured = {
                "load_per_core": [
                    line / snapshot.cpu_cores for line in snapshot.load_avg
                ],
                "memory_usage_percent": (
                    snapshot.memory_db["used"] / snapshot.memory_db["total"]
                )
                * 100,
                "disk_usage_percent": snapshot.disk_usage_percent,
            }

            return f"""
                Structured metrics: {json.dumps(structured, indent=2)}

                Raw context:
                {snapshot.raw_uptime}
                {snapshot.raw_free}
                """

    def _format_response(self, response: str) -> str:
        """Formatting response based on verbosity"""
        if self.verbosity == Verbosity.CONCISE:
            # extract only the summary and critical actions
            lines = response.split("\n")
            important = [
                line
                for line in lines
                if any(k in line.upper() for k in ["SUMMARY:", "CRITICAL:", "ACTION:"])
            ]

            # maxing 3 lines
            return "\n".join(important[3:])

        elif self.verbosity == Verbosity.DETAILED:
            # add in extra context
            return f"{response}\n\n[Context: Using {self.data_format.value} format]"

        # If normal is selected then we'll just return regular response
        return response

    # analyzing section
    def analyze(self) -> Dict[str, Any]:
        """
        Workflow: collect data -> analyze -> suggest
        Return: dict with summary, issues, and suggested commands (fixes)
        """

        # collecting the data
        self.console.print("[blue]Collecting system metrics...[/blue]")
        snapshot = self.collector.collect(
            include_raw=(self.data_format != DataFormat.STRUCTURED)
        )

        # preparing the data for AI
        data_str = self._prepare_data(snapshot)

        # ai analysis
        self.console.print("[green]Analyzing system state...[/green]")

        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=data_str),
        ]

        response = self.llm.invoke(messages)
        formatted_response = self._format_response(response.content)

        # parsing the response for commands
        suggested_commands = self._extract_commands(response.content)

        # saving to memory so the LLM can continue investigating
        self.memory.save_context(
            {"input": f"System analysis at {snapshot.load_avg}"},
            {"output": formatted_response},
        )

        return {
            "snapshot": snapshot,
            "analysis": formatted_response,
            "commands": suggested_commands,
        }

    def _extract_commands(self, response: str) -> List[str]:
        """Extracting suggested commands from AI responses"""
        commands = []
        lines = response.split("\n")

        for line in lines:
            line = line.strip()

            # looking for lines that looks like it has commands
            if line.startswith("$") or line.startswith("sudo") or "systemctl" in line:
                # clean up the command
                cmd = line.strip("$").strip()

                if cmd:
                    commands.append(cmd)

        return commands

    def run_fixes(self, commands: List[str]) -> List[Dict]:
        """Execute suggested fixes with user confirmation"""
        results = []

        for cmd in commands:
            self.console.print(f"\n[yellow]Suggested fix:[/yellow] {cmd}")

            if Confirm.ask("Execute this command?"):
                success, output = self.executor.execute(cmd)

                results.append(
                    {"command": cmd, "success": success, "output": output[:200]}
                )

                if success:
                    self.console.print("[green]Command executed[/green]")
                else:
                    self.console.print(f"[red]Failed: {output}[/red]")
            else:
                results.append(
                    {"command": cmd, "success": False, "output": "Skipped by user"}
                )

        return results

    def monitor_loop(self):
        """Main monitoring loop"""
        self.console.print(
            Panel.fit(
                "[bold cyan]AI System Monitor[/bold cyan]\n"
                "Analyzing system and suggesting optimizations",
                border_style="cyan",
            )
        )

        # analyze system
        result = self.analyze()

        # display analysis
        self.console.print("\n[bold]Analysis:[/bold]")
        self.console.print(result["analysis"])

        # if there are suggested fixes
        if result["commands"]:
            self.console.print(
                f"\n[yellow]Found {len(result['commands'])} suggested fixes[/yellow]"
            )

            if Confirm.ask("Would you like to review and execute fixes?"):
                fix_results = self.run_fixes(result["commands"])

                # print out the summary
                self.console.print("\n[bold]Execution Summary:[/bold]")
                for r in fix_results:
                    status = "[green]:)[/green]" if r["success"] else "[red]:([/red]"
                    self.console.print(f"{status} {r['command']}")
        else:
            self.console.print("\n[green]System is healthy, no fixes needed[/green]")


# intergration point for main cli
def run_ai_monitor(
    data_format: str = "hybrid", verbosity: str = "normal", auto_fix: bool = False
):
    """Entry point from main CLI"""
    try:
        monitor = AIMonitor(
            data_format=DataFormat[data_format.upper()],
            verbosity=Verbosity[verbosity.upper()],
        )
        monitor.monitor_loop()

    except Exception as err:
        Console().print(f"[red]Error: {str(err)}[/red]")
        Console().print("[yellow]Check the API key and try again[/yellow]")
