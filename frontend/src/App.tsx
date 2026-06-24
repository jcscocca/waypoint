import {
  BarChart3,
  Download,
  FileUp,
  MapPin,
  Route,
  ShieldAlert
} from "lucide-react";

const places = [
  { name: "Capitol Hill Station", detail: "Transit hub", status: "Ready" },
  { name: "Pike Place Market", detail: "Errand stop", status: "Ready" },
  { name: "South Lake Union", detail: "Work area", status: "Queued" }
];

const metrics = [
  { label: "Saved places", value: "3", tone: "cyan" },
  { label: "Input modes", value: "2", tone: "green" },
  { label: "Export formats", value: "CSV", tone: "amber" }
];

export default function App() {
  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Seattle reported incident context</p>
          <h1>Compare places you visit</h1>
        </div>
        <button className="icon-button" type="button" aria-label="Export dashboard">
          <Download size={18} />
        </button>
      </header>

      <section className="workspace" aria-labelledby="workspace-title">
        <div className="workspace-copy">
          <div className="section-kicker">
            <ShieldAlert size={18} />
            <span>Public dashboard scaffold</span>
          </div>
          <h2 id="workspace-title">Incident context workspace</h2>
          <p>
            Start a session, add places manually or in bulk, and compare
            reported incident context without uploading personal location
            history.
          </p>
        </div>

        <div className="actions" aria-label="Dashboard actions">
          <button type="button">
            <MapPin size={18} />
            Manual place
          </button>
          <button type="button">
            <FileUp size={18} />
            Bulk places
          </button>
          <button type="button">
            <Route size={18} />
            Compare routes
          </button>
        </div>
      </section>

      <section className="dashboard-grid" aria-label="Dashboard preview">
        <div className="panel span-two">
          <div className="panel-heading">
            <div>
              <p className="panel-label">Places</p>
              <h2>Review list</h2>
            </div>
            <MapPin size={20} />
          </div>
          <ul className="place-list">
            {places.map((place) => (
              <li key={place.name}>
                <div>
                  <strong>{place.name}</strong>
                  <span>{place.detail}</span>
                </div>
                <small>{place.status}</small>
              </li>
            ))}
          </ul>
        </div>

        <div className="panel">
          <div className="panel-heading">
            <div>
              <p className="panel-label">Analysis</p>
              <h2>Context summary</h2>
            </div>
            <BarChart3 size={20} />
          </div>
          <div className="summary-bars" aria-label="Incident context bars">
            <span style={{ width: "74%" }} />
            <span style={{ width: "56%" }} />
            <span style={{ width: "38%" }} />
          </div>
        </div>

        {metrics.map((metric) => (
          <div className={`stat panel ${metric.tone}`} key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </div>
        ))}
      </section>
    </main>
  );
}
