import { Building2 } from "lucide-react"

import type { WorkspacePublic } from "@/client"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useSwitchWorkspace } from "@/hooks/useWorkspace"
import { cn } from "@/lib/utils"

/** Pick the client whose company profile checks use. Shared by the website and the extension. */
export function WorkspaceSwitcher({
  workspaces,
  current,
  className,
}: {
  workspaces: WorkspacePublic[]
  current: WorkspacePublic
  className?: string
}) {
  const switcher = useSwitchWorkspace()
  return (
    <Select
      value={switcher.isPending ? switcher.variables : current.id}
      onValueChange={(id) => switcher.mutate(id)}
      disabled={switcher.isPending}
    >
      <SelectTrigger
        size="sm"
        aria-label="Client workspace"
        className={cn("max-w-64 min-w-0", className)}
      >
        <Building2 className="text-primary" aria-hidden="true" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent align="start">
        {workspaces.map((workspace) => (
          <SelectItem key={workspace.id} value={workspace.id}>
            {workspace.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
