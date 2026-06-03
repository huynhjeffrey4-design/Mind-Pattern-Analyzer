import { Link, useLocation } from "wouter";
import { Book, CheckSquare, Home, Sparkles, Settings, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";

function Sidebar() {
  const [location] = useLocation();
  const logout = useAuthStore((s) => s.logout);

  const links = [
    { href: "/dashboard", label: "Dashboard", icon: Home },
    { href: "/check-in", label: "Daily Check-in", icon: CheckSquare },
    { href: "/journal", label: "Journal", icon: Book },
    { href: "/insights", label: "Insights", icon: Sparkles },
    { href: "/settings", label: "Settings", icon: Settings },
  ];

  const handleLogout = () => {
    logout();
    window.location.href = "/login";
  };

  return (
    <aside className="w-64 border-r border-border bg-sidebar h-screen sticky top-0 flex flex-col pt-8 pb-4">
      <div className="px-6 mb-8">
        <h1 className="text-xl font-serif font-semibold text-sidebar-foreground tracking-tight">MindPattern</h1>
      </div>
      <nav className="flex-1 px-4 space-y-1">
        {links.map((link) => {
          const isActive =
            location === link.href ||
            (link.href !== "/dashboard" && location.startsWith(link.href));
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors text-sm font-medium",
                isActive
                  ? "bg-sidebar-primary text-sidebar-primary-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              )}
            >
              <Icon className="w-4 h-4" />
              {link.label}
            </Link>
          );
        })}
      </nav>
      <div className="px-4 pt-4 border-t border-border">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3 text-sm text-muted-foreground hover:text-foreground"
          onClick={handleLogout}
          data-testid="button-logout"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </Button>
      </div>
    </aside>
  );
}

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex bg-background w-full">
      <Sidebar />
      <main className="flex-1 min-w-0 flex flex-col">{children}</main>
    </div>
  );
}
