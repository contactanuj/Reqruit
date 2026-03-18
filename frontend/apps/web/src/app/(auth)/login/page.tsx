import { LoginForm } from "@/features/auth/components/LoginForm";

interface LoginPageProps {
  searchParams: Promise<{ redirect?: string }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const { redirect } = await searchParams;
  return (
    <main className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-md p-8">
        <h1 className="text-2xl font-bold mb-6">Sign in to Reqruit</h1>
        <LoginForm redirectTo={redirect} />
      </div>
    </main>
  );
}
