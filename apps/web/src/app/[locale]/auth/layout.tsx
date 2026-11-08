export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex w-full max-w-sm items-center justify-center min-h-[calc(100vh-4rem)] bg-muted/40 p-4">
      {children}
    </div>
  )
}
