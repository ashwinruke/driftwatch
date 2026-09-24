import subprocess


def run_tool(tool_name, argument):
    subprocess.run(["tool", "--name", tool_name, "--arg", argument], check=True)
