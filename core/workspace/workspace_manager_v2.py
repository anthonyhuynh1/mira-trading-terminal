"""
Enhanced workspace manager for context-based trading workspaces.
Each workspace is a complete trading environment with its own widget layout.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json
from datetime import datetime
from pathlib import Path


class WorkspaceType(Enum):
    """Pre-defined workspace types for common trading activities."""
    RESEARCH = "research"          # Deep analysis of single symbol
    DAY_TRADE = "day_trade"       # Fast execution, multiple symbols
    PORTFOLIO = "portfolio"        # Portfolio overview
    EARNINGS = "earnings"          # Earnings calendar focus
    NEWS = "news"                  # News monitoring
    CUSTOM = "custom"              # User-defined


@dataclass
class WidgetConfig:
    """Configuration for a widget in the workspace."""
    widget_type: str               # 'chart', 'quotes', 'fundamentals', etc.
    position: str                  # Dock position
    settings: Dict[str, Any]       # Widget-specific settings
    symbols: List[str]             # Symbols this widget tracks
    link_group: Optional[int] = None  # Sync group


@dataclass
class WorkspaceConfig:
    """Complete configuration for a workspace."""
    id: str
    name: str
    type: WorkspaceType
    primary_symbol: Optional[str]  # Main symbol for this workspace
    widgets: List[WidgetConfig] = field(default_factory=list)
    layout_state: Optional[str] = None  # Serialized Qt layout
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkspaceTemplates:
    """Pre-defined workspace templates for quick setup."""

    @staticmethod
    def research_template(symbol: str) -> WorkspaceConfig:
        """Template for in-depth research on a single symbol."""
        return WorkspaceConfig(
            id=f"research_{symbol}_{datetime.now().timestamp()}",
            name=f"Research: {symbol}",
            type=WorkspaceType.RESEARCH,
            primary_symbol=symbol,
            widgets=[
                WidgetConfig(
                    widget_type="chart",
                    position="center",
                    settings={"timeframe": "1D", "indicators": ["SMA", "RSI"]},
                    symbols=[symbol]
                ),
                WidgetConfig(
                    widget_type="fundamentals",
                    position="right",
                    settings={"view": "overview"},
                    symbols=[symbol]
                ),
                WidgetConfig(
                    widget_type="news",
                    position="bottom",
                    settings={"filter": "all"},
                    symbols=[symbol]
                ),
                WidgetConfig(
                    widget_type="quotes",
                    position="left",
                    settings={"depth": "L2"},
                    symbols=[symbol]
                )
            ]
        )

    @staticmethod
    def day_trade_template(symbols: List[str]) -> WorkspaceConfig:
        """Template for day trading multiple symbols."""
        return WorkspaceConfig(
            id=f"daytrade_{datetime.now().timestamp()}",
            name=f"Day Trade: {', '.join(symbols[:3])}...",
            type=WorkspaceType.DAY_TRADE,
            primary_symbol=symbols[0] if symbols else None,
            widgets=[
                WidgetConfig(
                    widget_type="chart",
                    position="center",
                    settings={"timeframe": "5Min", "indicators": ["VWAP", "Volume"]},
                    symbols=symbols,
                    link_group=1
                ),
                WidgetConfig(
                    widget_type="quotes",
                    position="right",
                    settings={"view": "tape"},
                    symbols=symbols,
                    link_group=1
                ),
                WidgetConfig(
                    widget_type="screener",
                    position="left",
                    settings={"filter": "volume_gainers"},
                    symbols=[]
                ),
                WidgetConfig(
                    widget_type="positions",
                    position="bottom",
                    settings={"account": "main"},
                    symbols=[]
                )
            ]
        )

    @staticmethod
    def portfolio_template() -> WorkspaceConfig:
        """Template for portfolio monitoring."""
        return WorkspaceConfig(
            id=f"portfolio_{datetime.now().timestamp()}",
            name="Portfolio Overview",
            type=WorkspaceType.PORTFOLIO,
            widgets=[
                WidgetConfig(
                    widget_type="positions",
                    position="center",
                    settings={"view": "detailed"},
                    symbols=[]
                ),
                WidgetConfig(
                    widget_type="performance",
                    position="top",
                    settings={"period": "1D"},
                    symbols=[]
                ),
                WidgetConfig(
                    widget_type="risk",
                    position="right",
                    settings={"metrics": ["var", "sharpe"]},
                    symbols=[]
                ),
                WidgetConfig(
                    widget_type="orders",
                    position="bottom",
                    settings={"status": "all"},
                    symbols=[]
                )
            ]
        )


class WorkspaceManagerV2:
    """
    Enhanced workspace manager for context-based trading.
    Manages multiple workspaces, each with their own widget configuration.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.workspaces_dir = data_dir / "workspaces"
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)

        self.workspaces: Dict[str, WorkspaceConfig] = {}
        self.active_workspace_id: Optional[str] = None
        self.templates = WorkspaceTemplates()

        self._load_all_workspaces()

    def create_workspace(
        self,
        name: str,
        workspace_type: WorkspaceType = WorkspaceType.CUSTOM,
        template: Optional[str] = None,
        **kwargs
    ) -> WorkspaceConfig:
        """Create a new workspace from template or custom."""
        if template == "research" and "symbol" in kwargs:
            workspace = self.templates.research_template(kwargs["symbol"])
        elif template == "day_trade" and "symbols" in kwargs:
            workspace = self.templates.day_trade_template(kwargs["symbols"])
        elif template == "portfolio":
            workspace = self.templates.portfolio_template()
        else:
            # Create custom workspace
            workspace = WorkspaceConfig(
                id=f"custom_{datetime.now().timestamp()}",
                name=name,
                type=workspace_type,
                primary_symbol=None
            )

        workspace.name = name  # Override template name if provided
        self.workspaces[workspace.id] = workspace
        self._save_workspace(workspace)

        return workspace

    def get_workspace(self, workspace_id: str) -> Optional[WorkspaceConfig]:
        """Get workspace by ID."""
        return self.workspaces.get(workspace_id)

    def list_workspaces(self) -> List[WorkspaceConfig]:
        """List all workspaces sorted by last accessed."""
        return sorted(
            self.workspaces.values(),
            key=lambda w: w.last_accessed,
            reverse=True
        )

    def activate_workspace(self, workspace_id: str) -> bool:
        """Activate a workspace."""
        if workspace_id not in self.workspaces:
            return False

        self.active_workspace_id = workspace_id
        workspace = self.workspaces[workspace_id]
        workspace.last_accessed = datetime.now()
        self._save_workspace(workspace)

        return True

    def update_workspace_layout(self, workspace_id: str, layout_state: str) -> None:
        """Update the Qt layout state for a workspace."""
        if workspace_id in self.workspaces:
            workspace = self.workspaces[workspace_id]
            workspace.layout_state = layout_state
            self._save_workspace(workspace)

    def add_widget_to_workspace(
        self,
        workspace_id: str,
        widget_config: WidgetConfig
    ) -> bool:
        """Add a widget to workspace."""
        if workspace_id not in self.workspaces:
            return False

        workspace = self.workspaces[workspace_id]
        workspace.widgets.append(widget_config)
        self._save_workspace(workspace)

        return True

    def remove_widget_from_workspace(
        self,
        workspace_id: str,
        widget_type: str,
        position: str
    ) -> bool:
        """Remove a widget from workspace."""
        if workspace_id not in self.workspaces:
            return False

        workspace = self.workspaces[workspace_id]
        workspace.widgets = [
            w for w in workspace.widgets
            if not (w.widget_type == widget_type and w.position == position)
        ]
        self._save_workspace(workspace)

        return True

    def delete_workspace(self, workspace_id: str) -> bool:
        """Delete a workspace."""
        if workspace_id not in self.workspaces:
            return False

        # Don't delete if it's the only workspace
        if len(self.workspaces) <= 1:
            return False

        workspace = self.workspaces.pop(workspace_id)
        workspace_file = self.workspaces_dir / f"{workspace_id}.json"
        workspace_file.unlink(missing_ok=True)

        # Activate another workspace if this was active
        if self.active_workspace_id == workspace_id:
            remaining = list(self.workspaces.keys())
            self.active_workspace_id = remaining[0] if remaining else None

        return True

    def _save_workspace(self, workspace: WorkspaceConfig) -> None:
        """Save workspace to disk."""
        workspace_file = self.workspaces_dir / f"{workspace.id}.json"

        data = {
            "id": workspace.id,
            "name": workspace.name,
            "type": workspace.type.value,
            "primary_symbol": workspace.primary_symbol,
            "widgets": [
                {
                    "widget_type": w.widget_type,
                    "position": w.position,
                    "settings": w.settings,
                    "symbols": w.symbols,
                    "link_group": w.link_group
                }
                for w in workspace.widgets
            ],
            "layout_state": workspace.layout_state,
            "created_at": workspace.created_at.isoformat(),
            "last_accessed": workspace.last_accessed.isoformat(),
            "metadata": workspace.metadata
        }

        with open(workspace_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_all_workspaces(self) -> None:
        """Load all workspaces from disk."""
        for workspace_file in self.workspaces_dir.glob("*.json"):
            try:
                with open(workspace_file) as f:
                    data = json.load(f)

                workspace = WorkspaceConfig(
                    id=data["id"],
                    name=data["name"],
                    type=WorkspaceType(data["type"]),
                    primary_symbol=data.get("primary_symbol"),
                    widgets=[
                        WidgetConfig(**w) for w in data.get("widgets", [])
                    ],
                    layout_state=data.get("layout_state"),
                    created_at=datetime.fromisoformat(data["created_at"]),
                    last_accessed=datetime.fromisoformat(data["last_accessed"]),
                    metadata=data.get("metadata", {})
                )

                self.workspaces[workspace.id] = workspace

            except Exception as e:
                print(f"Error loading workspace {workspace_file}: {e}")

        # Create default workspace if none exist
        if not self.workspaces:
            default = self.create_workspace(
                "Main Workspace",
                WorkspaceType.CUSTOM
            )
            self.active_workspace_id = default.id