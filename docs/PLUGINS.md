# Creating a Plugin

This guide explains how to create custom plugins for the Python Hedera Agent Kit.

## Plugin Structure

### Plugin Interface

Every plugin corresponds to the `Plugin` class:

```python
from typing import Callable, List
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.tool import Tool

class Plugin:
    def __init__(
        self,
        name: str,
        tools: Callable[[Context], List[Tool]],
        version: str | None = None,
        description: str | None = None,
    ):
        # ...
```

### Tool Interface

Each tool must assume the `Tool` class structure:

```python
from abc import ABC, abstractmethod
from typing import Any, Type
from hiero_sdk_python import Client
from pydantic import BaseModel
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import ToolResponse

class Tool(ABC):
    method: str
    name: str
    description: str
    parameters: Type[BaseModel]

    @abstractmethod
    async def execute(
        self, client: Client, context: Context, params: Any
    ) -> ToolResponse:
        """Execute the tool logic."""
        pass
```

See [hedera_agent_kit/shared/tool.py](../python/hedera_agent_kit/shared/tool.py) for the full definition.

## Step-by-Step Guide

### Step 1: Create Plugin Directory Structure

Recommended structure for your plugin:

```
my_custom_plugin/
├── __init__.py           # Plugin definition and exports
├── tools/
│   ├── __init__.py
│   └── my_tool.py        # Individual tool implementation
```

### Step 2: Implement Your Tool

Create your tool file (e.g., `tools/my_tool.py`). Use `pydantic` for parameter validation and `HederaParameterNormaliser` for type conversion.

> [!IMPORTANT]
> Some underlying frameworks depend solely on the Pydantic schemas, while others generate prompts based on the tool and parameter descriptions. Therefore, parameter descriptions must be **extremely detailed** to ensure the LLM understands exactly what to provide.

```python
from typing import Type, Any
from pydantic import BaseModel, Field
from hiero_sdk_python import Client, AccountId
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.models import ToolResponse
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import HederaParameterNormaliser

# 1. Define input parameters using Pydantic
class MyToolInput(BaseModel):
    required_param: str = Field(..., description="Detailed description of required parameter, e.g., 'The account ID to transfer to (0.0.x)'")
    optional_param: str | None = Field(None, description="Detailed description of optional parameter")

# 2. Define a normalized model (optional but recommended for internal logic)
class MyToolInputNormalised(BaseModel):
    required_param: AccountId
    optional_param: str | None

# 3. Implement the Tool class
class MyTool(Tool):
    def __init__(self):
        self.method = "my_tool"
        self.name = "My Custom Tool"
        self.description = "This tool performs a specific operation. It requires an account ID."
        self.parameters = MyToolInput

    async def execute(self, client: Client, context: Context, params: Any) -> ToolResponse:
        try:
            # Normalize parameters (e.g. convert string to AccountId)
            # This ensures the inputs are valid and in the correct object form
            normalized_params = MyToolInputNormalised(
                 required_param=AccountId.from_string(params.required_param),
                 optional_param=params.optional_param
            )

            # Your implementation here
            # result = await some_hedera_operation(client, normalized_params)
            # the operation does not need to be a hedera operation
            # result = await some_operation(normalized_params)

            return ToolResponse(
                result={"status": "success", "data": "some result"},
                human_message=f"Operation successful for {normalized_params.required_param}"
            )
        except Exception as e:
            return ToolResponse(
                result={"status": "error", "error": str(e)},
                human_message=f"Operation failed: {str(e)}"
            )
```

### Step 3: Create Plugin Definition

Create your plugin init file (`__init__.py`):

```python
from typing import List
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.plugin import Plugin
from hedera_agent_kit.shared.tool import Tool
from .tools.my_tool import MyTool

# Define a function that returns the list of tools
def get_my_tools(context: Context) -> List[Tool]:
    return [MyTool()]

# Create the Plugin instance
my_custom_plugin = Plugin(
    name="my-custom-plugin",
    version="1.0.0",
    description="A plugin for custom functionality",
    tools=get_my_tools,
)

# Export tool names for easy access
my_custom_plugin_tool_names = {
    "MY_TOOL": "my_tool"
}
```

### Step 4: Register Your Plugin

To use your plugin, include it in the `plugins` list when initializing the agent kit configuration.

#### LangChain Example

```python
from hiero_sdk_python import Client, Network
from hedera_agent_kit.langchain.toolkit import HederaLangchainToolkit
from hedera_agent_kit.shared.configuration import Configuration, Context, AgentMode
from my_custom_plugin import my_custom_plugin

# ... Client setup ...
client = Client(Network("testnet"))

config = Configuration(
    tools=[], # Optional: list of tool names (strings) to enable. Empty list or None enables all.
    plugins=[my_custom_plugin],  # Add your plugin here
    context=Context(mode=AgentMode.AUTONOMOUS)
)

toolkit = HederaLangchainToolkit(
    client=client,
    configuration=config
)
```

## Best Practices

### Parameter Validation
- Use `pydantic` models for robust input validation.
- Provide clear `description` fields for all parameters to help the LLM understand them.

### Tool Organization
- Group related tools by service type.
- Use consistent naming conventions (snake_case for methods/files).
- Follow the established directory structure.

### Transaction Handling
- Tools should handle errors gracefully and return descriptive `human_message` strings in `ToolResponse`.

## Publish and Register Your Plugin

To create a plugin to be used with the Hedera Agent Kit, you will need to create a plugin in your own repository, publish a PyPI package, and provide a description of the functionality included in that plugin, as well as the required and optional parameters.

Once you have a repository, published PyPI package, and a README with a description of the functionality included in that plugin in your plugin's repo, as well as the required and optional parameters, you can add it to the Hedera Agent Kit by forking and opening a Pull Request to:

1. Include the plugin as a bullet point under the **Available Third Party Plugin** section under the **Third Party Plugin** section in the [README.md in the hedera-agent-kit-py](https://github.com/hashgraph/hedera-agent-kit-py/blob/main/README.md). Include the name, a brief description, and a link to the repository with the README, as well as the URL linked to the published PyPI package.

2. All commits for your plugin **must be [DCO signed](https://wiki.linuxfoundation.org/dco)**, have the names of the tools & core actions exposed by the plugin, and **point to the exact version of the Python package**. To avoid having pull requests blocked in the future, always include a sign-off:

```text
Bonzo Plugin is a unified SDK to the Bonzo protocol, exposing the core actions (deposit, withdraw, repay, borrow) for decentralised lending and borrowing on Hedera:

PyPI: https://pypi.org/project/hak-bonzo-plugin/
Github repository: https://github.com/Bonzo-Labs/bonzoPlugin
Version: hak-bonzo-plugin==1.0.1
Status: Not validated by HAK team, v3-compatible release
```

Feel free to also [reach out to the Hedera Agent Kit maintainers on Discord](https://hedera.com/discord) or another channel so we can test out your plugin, include it in our docs, and let our community know thorough marketing and community channels.

Please also reach out in the Hedera Discord in the Support > developer-help-desk channel create an Issue in this repository for help building, publishing, and promoting your plugin

> [!NOTE]
> Short descriptions of each tool are required. Please see [docs/HEDERATOOLS.md](HEDERATOOLS.md) for reference on the expected format and level of detail.

### Plugin README Template

```markdown
## Plugin Name

This plugin was built by <?> for the <project, platform, etc>. It was built to enable <who?> to <do what?>

### Installation

'''bash
pip install <plugin-name>
'''

### Usage

'''python
from hedera_agent_kit.langchain.toolkit import HederaLangchainToolkit
from hedera_agent_kit.shared.configuration import Configuration
from my_plugin import my_custom_plugin

# ... Client setup ...
config = Configuration(plugins=[my_custom_plugin])
toolkit = HederaLangchainToolkit(client=client, configuration=config)
'''

### Functionality

**Plugin Name**
_High level description of the plugin_

### `MY_TOOL_NAME`

_Description of what the tool does._

#### Parameters

| Parameter        | Type    | Required | Description                                       |
|------------------|---------|----------|---------------------------------------------------|
| `param_name`     | `str`   | ✅        | Description of the parameter.                     |
| `optional_param` | `int`   | ❌        | Description of the optional parameter.            |

#### Example Prompts

_Example prompt 1_
_Example prompt 2_

```
