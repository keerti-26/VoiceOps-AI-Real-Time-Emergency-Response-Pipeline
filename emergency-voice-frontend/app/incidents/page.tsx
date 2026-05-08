"use client";

import { useEffect, useState } from "react";

type Incident = {
  incident_id: string;
  emergency_type?: string;
  severity?: string;
  location?: string;
  status?: string;
  summary?: string;
  created_at?: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;


export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");
  const [severityFilter, setSeverityFilter] = useState("all");

  const fetchIncidents = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/incidents`);
      const data = await response.json();
      setIncidents(data);
    } catch (error) {
      console.error("Failed to fetch incidents:", error);
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (incidentId: string, status: string) => {
    try {
      await fetch(`${API_BASE}/incidents/${incidentId}?status=${status}`, {
        method: "PUT",
      });

      await fetchIncidents();
    } catch (error) {
      console.error("Failed to update status:", error);
    }
  };

  useEffect(() => {
    fetchIncidents();

    const interval = setInterval(fetchIncidents, 5000);
    return () => clearInterval(interval);
  }, []);

  const filteredIncidents = incidents.filter((incident) => {
    const statusMatch =
      statusFilter === "all" || incident.status === statusFilter;

    const severityMatch =
      severityFilter === "all" || incident.severity === severityFilter;

    return statusMatch && severityMatch;
  });

  const severityClass = (severity?: string) => {
    switch (severity) {
      case "critical":
        return "bg-red-100 text-red-700 border-red-300";
      case "high":
        return "bg-orange-100 text-orange-700 border-orange-300";
      case "medium":
        return "bg-yellow-100 text-yellow-700 border-yellow-300";
      case "low":
        return "bg-green-100 text-green-700 border-green-300";
      default:
        return "bg-gray-100 text-gray-700 border-gray-300";
    }
  };

  const statusClass = (status?: string) => {
    switch (status) {
      case "new":
        return "bg-blue-100 text-blue-700";
      case "in_review":
        return "bg-purple-100 text-purple-700";
      case "escalated":
        return "bg-red-100 text-red-700";
      case "closed":
        return "bg-gray-200 text-gray-700";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  return (
    <main className="min-h-screen bg-gray-100 p-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Emergency Incident Dashboard</h1>
            <p className="text-gray-600">
              Live view of AI-extracted emergency incidents from Cosmos DB.
            </p>
          </div>

          <button
            onClick={fetchIncidents}
            className="rounded bg-black px-4 py-2 text-white"
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4">
          <div className="rounded bg-white p-4 shadow">
            <p className="text-sm text-gray-500">Total</p>
            <p className="text-2xl font-bold">{incidents.length}</p>
          </div>

          <div className="rounded bg-white p-4 shadow">
            <p className="text-sm text-gray-500">Critical</p>
            <p className="text-2xl font-bold">
              {incidents.filter((i) => i.severity === "critical").length}
            </p>
          </div>

          <div className="rounded bg-white p-4 shadow">
            <p className="text-sm text-gray-500">New</p>
            <p className="text-2xl font-bold">
              {incidents.filter((i) => i.status === "new").length}
            </p>
          </div>

          <div className="rounded bg-white p-4 shadow">
            <p className="text-sm text-gray-500">Escalated</p>
            <p className="text-2xl font-bold">
              {incidents.filter((i) => i.status === "escalated").length}
            </p>
          </div>
        </div>

        <div className="mb-6 flex gap-4 rounded bg-white p-4 shadow">
          <select
            className="rounded border p-2"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="new">New</option>
            <option value="in_review">In Review</option>
            <option value="escalated">Escalated</option>
            <option value="closed">Closed</option>
          </select>

          <select
            className="rounded border p-2"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        <div className="space-y-4">
          {filteredIncidents.map((incident) => (
            <div
              key={incident.incident_id}
              className="rounded-xl bg-white p-5 shadow"
            >
              <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-xl font-bold">
                    {incident.incident_id}
                  </h2>
                  <p className="text-sm text-gray-500">
                    {incident.created_at
                      ? new Date(incident.created_at).toLocaleString()
                      : "No timestamp"}
                  </p>
                </div>

                <div className="flex gap-2">
                  <span
                    className={`rounded border px-3 py-1 text-sm font-semibold ${severityClass(
                      incident.severity
                    )}`}
                  >
                    {incident.severity || "unknown"}
                  </span>

                  <span
                    className={`rounded px-3 py-1 text-sm font-semibold ${statusClass(
                      incident.status
                    )}`}
                  >
                    {incident.status || "unknown"}
                  </span>
                </div>
              </div>

              <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-3">
                <p>
                  <b>Type:</b> {incident.emergency_type || "Unknown"}
                </p>
                <p>
                  <b>Location:</b> {incident.location || "Missing"}
                </p>
                <p>
                  <b>Status:</b> {incident.status || "Unknown"}
                </p>
              </div>

              <p className="mb-4 text-gray-700">
                <b>Summary:</b> {incident.summary || "No summary available"}
              </p>

              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => updateStatus(incident.incident_id, "in_review")}
                  className="rounded bg-purple-600 px-3 py-2 text-sm text-white"
                >
                  Mark In Review
                </button>

                <button
                  onClick={() => updateStatus(incident.incident_id, "escalated")}
                  className="rounded bg-red-600 px-3 py-2 text-sm text-white"
                >
                  Escalate
                </button>

                <button
                  onClick={() => updateStatus(incident.incident_id, "closed")}
                  className="rounded bg-gray-700 px-3 py-2 text-sm text-white"
                >
                  Close
                </button>
              </div>
            </div>
          ))}

          {filteredIncidents.length === 0 && (
            <div className="rounded bg-white p-8 text-center shadow">
              <p className="text-gray-500">No incidents found.</p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}