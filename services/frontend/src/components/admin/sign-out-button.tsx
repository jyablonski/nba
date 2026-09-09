import { Button } from "@/components/ui/button";
import { signOut } from "@/auth";

export function SignOutButton() {
  return (
    <form
      action={async () => {
        "use server";
        await signOut({ redirectTo: "/admin/signin" });
      }}
    >
      <Button type="submit" variant="outline" size="sm">
        Sign out
      </Button>
    </form>
  );
}
