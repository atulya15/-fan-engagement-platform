import { Sidebar } from "@/components/Sidebar";
import { BackgroundArt } from "@/components/BackgroundArt";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <BackgroundArt />
      <div className="flex min-h-full">
        <Sidebar />
        <div className="flex-1 pt-16 lg:pl-64 lg:pt-0">{children}</div>
      </div>
    </>
  );
}
