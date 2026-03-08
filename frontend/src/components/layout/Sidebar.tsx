"use client";

import React, { useState, createContext, useContext } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { 
  LayoutDashboard, 
  Lightbulb, 
  BarChart3, 
  Briefcase, 
  FileText, 
  Settings,
  ShieldCheck,
  Menu, 
  X,
  ChevronRight,
  LogOut,
} from "lucide-react";
import { MobileBottomNav } from "./MobileBottomNav";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/contexts/AuthContext";
import { usePermissions } from "@/hooks/usePermissions";
import { UserRole } from "@/types/api";

interface SidebarLink {
  label: string;
  href: string;
  icon: React.ReactNode;
  permission?: string;
}

interface SidebarContextProps {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  animate: boolean;
}

const SidebarContext = createContext<SidebarContextProps | undefined>(
  undefined
);

export const useSidebar = () => {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error("useSidebar must be used within a SidebarProvider");
  }
  return context;
};

export const SidebarProvider = ({
  children,
  open: openProp,
  setOpen: setOpenProp,
  animate = true,
}: {
  children: React.ReactNode;
  open?: boolean;
  setOpen?: React.Dispatch<React.SetStateAction<boolean>>;
  animate?: boolean;
}) => {
  const [openState, setOpenState] = useState(false);

  const open = openProp !== undefined ? openProp : openState;
  const setOpen = setOpenProp !== undefined ? setOpenProp : setOpenState;

  return (
    <SidebarContext.Provider value={{ open, setOpen, animate }}>
      {children}
    </SidebarContext.Provider>
  );
};

export const Sidebar = ({
  children,
  open,
  setOpen,
  animate,
}: {
  children: React.ReactNode;
  open?: boolean;
  setOpen?: React.Dispatch<React.SetStateAction<boolean>>;
  animate?: boolean;
}) => {
  return (
    <SidebarProvider open={open} setOpen={setOpen} animate={animate}>
      {children}
    </SidebarProvider>
  );
};

export const SidebarBody = (props: React.ComponentProps<typeof motion.div>) => {
  return (
    <>
      <DesktopSidebar {...props} />
      <MobileSidebar {...(props as React.ComponentProps<"div">)} />
    </>
  );
};

export const DesktopSidebar = ({
  className,
  children,
  ...props
}: React.ComponentProps<typeof motion.div>) => {
  const { open, setOpen, animate } = useSidebar();
  return (
    <motion.div
      className={cn(
        "h-full px-4 py-4 hidden md:flex md:flex-col bg-slate-900 w-[280px] flex-shrink-0 border-r border-slate-800",
        className
      )}
      animate={{
        width: animate ? (open ? "280px" : "80px") : "280px",
      }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      {...props}
    >
      {children}
    </motion.div>
  );
};

export const MobileSidebar = ({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) => {
  const { open, setOpen } = useSidebar();
  return (
    <>
      <div
        className={cn(
          "h-16 px-4 py-4 flex flex-row md:hidden items-center justify-between bg-slate-900 w-full border-b border-slate-800"
        )}
        {...props}
      >
        <div className="flex justify-between items-center z-20 w-full">
          <span className="text-lg font-bold text-white">FuelHedge</span>
          <Menu
            className="text-slate-200 cursor-pointer"
            onClick={() => setOpen(!open)}
          />
        </div>
        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ x: "-100%", opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: "-100%", opacity: 0 }}
              transition={{
                duration: 0.3,
                ease: "easeInOut",
              }}
              className={cn(
                "fixed h-full w-full inset-0 bg-slate-900 p-10 z-[100] flex flex-col justify-between",
                className
              )}
            >
              <div
                className="absolute right-10 top-10 z-50 text-slate-200 cursor-pointer"
                onClick={() => setOpen(!open)}
              >
                <X />
              </div>
              {children}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  );
};

export const SidebarLinkItem = ({
  link,
  className,
  active = false,
}: {
  link: SidebarLink;
  className?: string;
  active?: boolean;
}) => {
  const { open, animate } = useSidebar();
  return (
    <Link
      to={link.href}
      className={cn(
        "flex items-center justify-start gap-3 group/sidebar py-3 px-3 rounded-lg cursor-pointer transition-all",
        active 
          ? "bg-primary-600 text-white shadow-lg shadow-primary-600/30" 
          : "text-slate-400 hover:bg-slate-800 hover:text-slate-200",
        className
      )}
    >
      <div className="flex-shrink-0">
        {link.icon}
      </div>
      <motion.span
        animate={{
          display: animate ? (open ? "inline-block" : "none") : "inline-block",
          opacity: animate ? (open ? 1 : 0) : 1,
        }}
        className="text-sm font-medium whitespace-pre !p-0 !m-0"
      >
        {link.label}
      </motion.span>
      {active && open && (
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          className="ml-auto"
        >
          <ChevronRight className="h-4 w-4" />
        </motion.div>
      )}
    </Link>
  );
};

export const AppShell = ({ children }: { children: React.ReactNode }) => {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const { user, logout } = useAuth();
  const { canViewPage } = usePermissions();

  const links: SidebarLink[] = [
    {
      label: "Dashboard",
      href: "/",
      icon: <LayoutDashboard className="h-5 w-5 flex-shrink-0" />,
    },
    {
      label: "Recommendations",
      href: "/recommendations",
      icon: <Lightbulb className="h-5 w-5 flex-shrink-0" />,
      permission: "recommendations",
    },
    {
      label: "Analytics",
      href: "/analytics",
      icon: <BarChart3 className="h-5 w-5 flex-shrink-0" />,
      permission: "analytics",
    },
    {
      label: "Positions",
      href: "/positions",
      icon: <Briefcase className="h-5 w-5 flex-shrink-0" />,
      permission: "positions",
    },
    {
      label: "Compliance",
      href: "/compliance",
      icon: <ShieldCheck className="h-5 w-5 flex-shrink-0" />,
      permission: "compliance",
    },
    {
      label: "Audit Log",
      href: "/audit",
      icon: <FileText className="h-5 w-5 flex-shrink-0" />,
      permission: "audit",
    },
    {
      label: "Settings",
      href: "/settings",
      icon: <Settings className="h-5 w-5 flex-shrink-0" />,
      permission: "settings",
    },
  ];

  const visibleLinks = links.filter(
    (link) => !link.permission || canViewPage(link.permission)
  );

  const getRoleBadgeVariant = (role: UserRole) => {
    switch (role) {
      case UserRole.ADMIN:
        return "destructive";
      case UserRole.CFO:
        return "warning";
      case UserRole.RISK_MANAGER:
        return "success";
      default:
        return "secondary";
    }
  };

  const getRoleLabel = (role: UserRole) => {
    switch (role) {
      case UserRole.ADMIN:
        return "Admin";
      case UserRole.CFO:
        return "CFO";
      case UserRole.RISK_MANAGER:
        return "Risk Manager";
      case UserRole.ANALYST:
        return "Analyst";
      default:
        return role;
    }
  };

  const getUserInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="flex h-screen w-full bg-slate-950">
      <Sidebar open={open} setOpen={setOpen}>
        <SidebarBody className="justify-between gap-10">
          <div className="flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
            <div className="mb-8">
              <motion.div
                animate={{
                  justifyContent: open ? "flex-start" : "center",
                }}
                className="flex items-center gap-3 px-3"
              >
                <div className="h-8 w-8 bg-primary-600 rounded-lg flex items-center justify-center flex-shrink-0 shadow-lg shadow-primary-600/30">
                  <span className="text-white font-bold text-sm">FH</span>
                </div>
                <motion.span
                  animate={{
                    display: open ? "inline-block" : "none",
                    opacity: open ? 1 : 0,
                  }}
                  className="font-bold text-xl text-white whitespace-pre"
                >
                  FuelHedge
                </motion.span>
              </motion.div>
            </div>
            <div className="flex flex-col gap-2">
              {visibleLinks.map((link, idx) => (
                <SidebarLinkItem
                  key={idx}
                  link={link}
                  active={location.pathname === link.href}
                />
              ))}
            </div>
          </div>
          <div className="border-t border-slate-800 pt-4">
            {/* User Profile Section */}
            <div
              className={cn(
                "flex items-center gap-3 px-3 py-3 rounded-lg mb-2"
              )}
            >
              <Avatar className="h-8 w-8 flex-shrink-0 ring-2 ring-primary-600/20">
                <AvatarFallback className="bg-primary-600 text-white text-sm font-semibold">
                  {user ? getUserInitials(user.full_name) : 'U'}
                </AvatarFallback>
              </Avatar>
              <motion.div
                animate={{
                  display: open ? "flex" : "none",
                  opacity: open ? 1 : 0,
                }}
                className="flex flex-col min-w-0"
              >
                <span className="text-sm font-medium text-white truncate">
                  {user?.full_name || 'User'}
                </span>
                <div className="flex items-center gap-2 mt-1">
                  <Badge 
                    variant={user ? getRoleBadgeVariant(user.role) : "secondary"}
                    className="text-xs px-2 py-0 h-5 border-none"
                  >
                    {user ? getRoleLabel(user.role) : 'Guest'}
                  </Badge>
                </div>
              </motion.div>
            </div>

            {/* Logout Button */}
            <button
              onClick={async () => {
                await logout();
                window.location.href = '/login';
              }}
              className={cn(
                "flex items-center gap-3 px-3 py-3 rounded-lg w-full transition-all duration-200",
                "text-slate-400 hover:text-red-400 hover:bg-red-950/20",
                "group"
              )}
            >
              <LogOut className="h-5 w-5 flex-shrink-0 group-hover:text-red-400 transition-colors" />
              <motion.span
                animate={{
                  display: open ? "inline-block" : "none",
                  opacity: open ? 1 : 0,
                }}
                className="text-sm font-medium group-hover:text-red-400 transition-colors"
              >
                Logout
              </motion.span>
            </button>
          </div>
        </SidebarBody>
      </Sidebar>
      <div className="flex-1 bg-slate-950 overflow-auto pb-16 md:pb-0">
        {children}
      </div>
      <MobileBottomNav />
    </div>
  );
};
