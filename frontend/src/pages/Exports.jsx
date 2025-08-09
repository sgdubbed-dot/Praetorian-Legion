import React, { useEffect, useState } from "react";
import { api, phoenixTime } from "../api";

export default function Exports() {
  const [items, setItems] = useState([]);
  const [recipeName, setRecipeName] = useState("Warm+Hot last 7 days with LinkedIn handle");
  const [modalOpen, setModalOpen] = useState(false);
  const [filters, setFilters] = useState({ priority_state: ["warm","hot"], platforms: [], has_linkedin: true, tags: [] });

  const refresh = async () => setItems((await api.get(`/exports`)).data);
  useEffect(() => { refresh(); }, []);

  const createRecipe = async () => {
    await api.post(`/exports/recipe`, { recipe_name: recipeName, filter_spec: filters });
    await refresh();
  };
  const generate = async () => {
    await api.post(`/exports/generate`, { recipe_name: recipeName });
    await refresh();
  };

  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Exports</h2>
      <div className="bg-white rounded shadow p-3 mb-4 grid grid-cols-1 md:grid-cols-4 gap-2">
        <input className="border rounded px-2 py-1" value={recipeName} onChange={(e) => setRecipeName(e.target.value)} />
        <button onClick={() => setModalOpen(true)} className="px-3 py-1 bg-neutral-800 text-white rounded">Create Recipe</button>
        <button onClick={generate} className="px-3 py-1 bg-blue-600 text-white rounded">Generate</button>
      </div>

      <div className="bg-white rounded shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-neutral-100 text-left">
              <th className="p-2">Recipe</th>
              <th className="p-2">Rows</th>
              <th className="p-2">File</th>
              <th className="p-2">Generated</th>
            </tr>
          </thead>
          <tbody>
            {items.map((e) => (
              <tr key={e.id} className="border-t">
                <td className="p-2">{e.recipe_name}</td>
                <td className="p-2">{e.row_count}</td>
                <td className="p-2">{e.file_url ? (<a className="text-blue-600 underline" href={e.file_url}>Download CSV</a>) : '-'}</td>
                <td className="p-2">{phoenixTime(e.generated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modalOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center">
          <div className="bg-white rounded shadow p-4 w-full max-w-md">
            <div className="text-lg font-semibold mb-2">Create Recipe</div>
            <div className="space-y-2 text-sm">
              <div>
                <div className="font-medium">Priority states</div>
                <div className="flex gap-2">
                  {["hot","warm","cold"].map(s => (
                    <label key={s} className="flex items-center gap-1">
                      <input type="checkbox" checked={(filters.priority_state||[]).includes(s)} onChange={(e) => {
                        const arr = new Set(filters.priority_state||[]);
                        e.target.checked ? arr.add(s) : arr.delete(s);
                        setFilters({ ...filters, priority_state: Array.from(arr) });
                      }} /> {s}
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <div className="font-medium">Platforms (tags)</div>
                <input className="w-full border rounded px-2 py-1" placeholder="comma separated" onChange={(e) => setFilters({ ...filters, platforms: e.target.value.split(',').map(v => v.trim()).filter(Boolean) })} />
              </div>
              <div>
                <label className="flex items-center gap-2"><input type="checkbox" checked={!!filters.has_linkedin} onChange={(e) => setFilters({ ...filters, has_linkedin: e.target.checked })} />Has LinkedIn handle</label>
              </div>
              <div>
                <div className="font-medium">Tags</div>
                <input className="w-full border rounded px-2 py-1" placeholder="comma separated" onChange={(e) => setFilters({ ...filters, tags: e.target.value.split(',').map(v => v.trim()).filter(Boolean) })} />
              </div>
            </div>
            <div className="mt-3 flex gap-2 justify-end">
              <button onClick={() => setModalOpen(false)} className="px-3 py-1 bg-neutral-200 rounded">Cancel</button>
              <button onClick={() => { setModalOpen(false); createRecipe(); }} className="px-3 py-1 bg-blue-600 text-white rounded">Save Recipe</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}