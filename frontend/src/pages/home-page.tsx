import { Leaf, ListTodo, MapPin, Sprout } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/auth-context";

export function HomePage() {
  const { user, activeHousehold, households } = useAuth();

  return (
    <div className="space-y-6">
      <section className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">
          Hello{user ? `, ${user.display_name}` : ""}
        </h1>
        <p className="text-muted-foreground">
          {activeHousehold
            ? `Active household: ${activeHousehold.name}`
            : "Create or join a household to start managing plants."}
        </p>
      </section>

      {!activeHousehold && (
        <Card>
          <CardHeader>
            <CardTitle>No household yet</CardTitle>
            <CardDescription>
              Create a household or accept an invite from a household admin.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button asChild>
              <Link to="/household">Manage households</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {activeHousehold && (
        <div className="grid gap-4 sm:grid-cols-2">
          <Link to="/plants" className="block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <FeatureCard
              icon={Sprout}
              title="Plants"
              description="Browse your collection, add specimens, and manage photos."
            />
          </Link>
          <FeatureCard
            icon={ListTodo}
            title="Tasks & watering"
            description="Adaptive watering engine ships next on the roadmap."
          />
          <FeatureCard
            icon={MapPin}
            title="Layout"
            description="Rooms, shelves, and placements coming soon."
          />
          <FeatureCard
            icon={Leaf}
            title="Care intelligence"
            description="Recommendations that improve with your feedback."
          />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Your households</CardTitle>
        </CardHeader>
        <CardContent>
          {households.length === 0 ? (
            <p className="text-sm text-muted-foreground">None yet.</p>
          ) : (
            <ul className="divide-y divide-border text-sm">
              {households.map((h) => (
                <li key={h.id} className="flex items-center justify-between py-2">
                  <span className="font-medium">{h.name}</span>
                  <span className="text-muted-foreground capitalize">{h.role}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: typeof Leaf;
  title: string;
  description: string;
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-start gap-3 space-y-0">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
          <Icon className="h-4 w-4" />
        </span>
        <div>
          <CardTitle className="text-base">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </div>
      </CardHeader>
    </Card>
  );
}
