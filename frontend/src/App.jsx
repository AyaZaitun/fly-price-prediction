import { useEffect, useState } from 'react';

const airlineOptions = ['AirAsia', 'Air_India', 'GO_FIRST', 'Indigo', 'SpiceJet', 'Vistara'];
const cityOptions = ['Bangalore', 'Chennai', 'Delhi', 'Hyderabad', 'Kolkata', 'Mumbai'];
const timeOptions = ['Early Morning', 'Morning', 'Afternoon', 'Evening', 'Night', 'Late Night'];
const monthOptions = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const holidayOptions = [
  { label: 'No', value: 'No' },
  { label: 'Yes', value: 'Yes' },
];
const tripPurposeOptions = ['Business', 'Leisure', 'Family Visit', 'Medical', 'Study', 'Other'];
const stopOptions = [
  { label: 'Non-stop', value: 'zero' },
  { label: '1 Stop', value: 'one' },
  { label: '2+ Stops', value: 'two_or_more' },
];
const classOptions = ['Economy', 'Business'];
const plannerFields = new Set(['flight', 'month', 'holiday', 'trip_purpose']);

const initialForm = {
  airline: '',
  flight: '',
  source_city: '',
  departure_time: '',
  stops: '',
  arrival_time: '',
  destination_city: '',
  class: '',
  duration: '5.5',
  days_left: '20',
  month: '',
  holiday: '',
  trip_purpose: '',
};

const navItems = [
  { label: 'Home', href: '#home' },
  { label: 'Predict', href: '#predict' },
  { label: 'About', href: '#about' },
];

function App() {
  const [form, setForm] = useState(initialForm);
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [tripContext, setTripContext] = useState({});
  const [serverError, setServerError] = useState('');
  const [chatOpen, setChatOpen] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState('');

  useEffect(() => {
    if (chatOpen) {
      document.getElementById('ai-assistant')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [chatOpen]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    if (result && plannerFields.has(name)) {
      setTripContext((current) => ({ ...current, [name]: value || null }));
    }
    setErrors((current) => ({ ...current, [name]: '' }));
    setServerError('');
  };

  const validateForm = () => {
    const nextErrors = {};

    if (!form.airline) nextErrors.airline = 'Please select an airline.';
    if (!form.source_city) nextErrors.source_city = 'Please select a source city.';
    if (!form.departure_time) nextErrors.departure_time = 'Please select departure time.';
    if (!form.stops) nextErrors.stops = 'Please choose a stop option.';
    if (!form.arrival_time) nextErrors.arrival_time = 'Please select arrival time.';
    if (!form.destination_city) nextErrors.destination_city = 'Please select a destination city.';
    if (!form.class) nextErrors.class = 'Please choose a cabin class.';
    if (!form.duration || Number(form.duration) <= 0) nextErrors.duration = 'Duration must be greater than 0.';
    if (!form.days_left || Number(form.days_left) < 1) nextErrors.days_left = 'Days left must be at least 1.';
    if (form.source_city && form.destination_city && form.source_city === form.destination_city) {
      nextErrors.destination_city = 'Source and destination cannot be the same.';
    }

    if (form.duration !== '' && Number(form.duration) < 0) {
      nextErrors.duration = 'Duration cannot be negative.';
    }
    if (form.days_left !== '' && Number(form.days_left) < 0) {
      nextErrors.days_left = 'Days left cannot be negative.';
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const submitPrediction = async (event) => {
    event.preventDefault();
    setServerError('');
    setResult(null);

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          airline: form.airline,
          flight: form.flight || '',
          source_city: form.source_city,
          departure_time: form.departure_time,
          stops: form.stops,
          arrival_time: form.arrival_time,
          destination_city: form.destination_city,
          class: form.class,
          duration: Number(form.duration),
          days_left: Number(form.days_left),
          month: form.month || '',
          holiday: form.holiday || '',
          trip_purpose: form.trip_purpose || '',
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        const message = data?.detail || "We couldn't calculate the price right now. Please check your flight details and try again.";
        throw new Error(message);
      }

      const nextTripContext = {
        ...data.trip_details,
        predicted_price_inr: Number(data.predicted_price_inr),
        predicted_price_jod: Number(data.predicted_price_jod),
      };
      const freshConversationId = `trip-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

      setTripContext(nextTripContext);
      setResult({
        inr: Number(data.predicted_price_inr),
        jod: Number(data.predicted_price_jod),
        aiSummary: data.ai_summary || 'Your price estimate is ready. This is a practical planning estimate based on your trip details.',
        conversationId: freshConversationId,
      });
      setChatMessages([
        {
          role: 'assistant',
          text: 'Hi! I can help with your trip. Ask me about places to visit, food, travel tips, or what to pack.',
        },
      ]);
      setChatOpen(true);
    } catch (error) {
      setServerError(error.message || "We couldn't calculate the price right now. Please check your flight details and try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const submitChatMessage = async (event) => {
    event.preventDefault();
    const trimmed = chatInput.trim();
    if (!trimmed || !result) return;

    const userMessage = trimmed;
    setChatInput('');
    setChatError('');
    setChatMessages((current) => [...current, { role: 'user', text: userMessage }]);
    setChatLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          trip_context: tripContext,
          conversation_id: result?.conversationId || `trip-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail || 'The AI assistant is temporarily unavailable.');
      }

      setChatMessages((current) => [...current, { role: 'assistant', text: data.assistant_response }]);
      setTripContext(data.trip_context || tripContext);
      if (data.conversation_id) {
        setResult((current) => ({ ...current, conversationId: data.conversation_id }));
      }
    } catch (error) {
      setChatError(error.message || 'The AI assistant is temporarily unavailable.');
      setChatMessages((current) => [...current, { role: 'assistant', text: 'I don’t have reliable current information about that.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  const resetForm = () => {
    setForm(initialForm);
    setErrors({});
    setResult(null);
    setTripContext({});
    setServerError('');
    setChatOpen(false);
    setChatMessages([]);
    setChatInput('');
    setChatError('');
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur-sm sticky top-0 z-20">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 md:px-8">
          <div>
            <p className="text-2xl font-extrabold tracking-tight text-slate-900">FlyPrice</p>
            <p className="text-xs font-medium text-slate-500">Predict your flight price before you book.</p>
          </div>

          <nav className="hidden items-center gap-8 md:flex">
            {navItems.map((item) => (
              <a key={item.label} href={item.href} className="text-sm font-medium text-slate-600 transition hover:text-brand-600">
                {item.label}
              </a>
            ))}
          </nav>
        </div>
      </header>

      <main id="home">
        <section className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-16 md:px-8 lg:grid-cols-[1.2fr_0.8fr] lg:py-20">
          <div>
            <div className="inline-flex items-center rounded-full border border-brand-100 bg-brand-50 px-3 py-1 text-sm font-semibold text-brand-700">
              Travel smarter with AI
            </div>
            <h1 className="mt-6 text-4xl font-extrabold tracking-tight text-slate-900 md:text-6xl">
              Know Your Flight Price Before You Book.
            </h1>
            <p className="mt-5 max-w-xl text-lg text-slate-600">
              FlyPrice AI uses machine learning to estimate flight ticket prices from your travel details, helping you understand what you might expect to pay before booking.
            </p>
            <div className="mt-8 flex flex-col gap-4 sm:flex-row">
              <a href="#predict" className="inline-flex items-center justify-center rounded-full bg-brand-600 px-6 py-3 text-sm font-semibold text-white shadow-soft transition hover:bg-brand-700">
                Predict My Flight
              </a>
              <a href="#about" className="inline-flex items-center justify-center rounded-full border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-brand-200 hover:text-brand-700">
                How It Works
              </a>
            </div>
          </div>

          <div className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-soft">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-500">Sample estimate</p>
                <p className="mt-2 text-3xl font-bold text-slate-900">₹18,400</p>
              </div>
              <div className="rounded-2xl bg-gradient-to-br from-brand-100 to-indigo-100 p-3 text-2xl">✈️</div>
            </div>
            <div className="mt-6 space-y-4">
              <div className="rounded-2xl bg-slate-50 p-4">
                <p className="text-sm text-slate-500">Route</p>
                <p className="mt-1 font-semibold">Delhi → Mumbai</p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-4">
                <p className="text-sm text-slate-500">Cabin</p>
                <p className="mt-1 font-semibold">Economy • 5.5 hrs</p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-4">
                <p className="text-sm text-slate-500">Planning window</p>
                <p className="mt-1 font-semibold">20 days left</p>
              </div>
            </div>
          </div>
        </section>

        <section id="predict" className="mx-auto max-w-6xl px-4 py-8 md:px-8">
          <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-soft md:p-8">
              <div className="mb-6">
                <p className="text-sm font-semibold uppercase tracking-[0.12em] text-brand-600">Predict</p>
                <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">Predict Your Flight Price</h2>
              </div>

              <form className="space-y-5" onSubmit={submitPrediction} noValidate>
                <div className="grid gap-5 md:grid-cols-2">
                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Airline</label>
                    <select name="airline" value={form.airline} onChange={handleChange} className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100">
                      <option value="">Select airline</option>
                      {airlineOptions.map((item) => (
                        <option key={item} value={item}>{item}</option>
                      ))}
                    </select>
                    {errors.airline && <p className="mt-1 text-sm text-red-600">{errors.airline}</p>}
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Source City</label>
                    <select name="source_city" value={form.source_city} onChange={handleChange} className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100">
                      <option value="">Select source city</option>
                      {cityOptions.map((item) => (
                        <option key={item} value={item}>{item}</option>
                      ))}
                    </select>
                    {errors.source_city && <p className="mt-1 text-sm text-red-600">{errors.source_city}</p>}
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Destination City</label>
                    <select name="destination_city" value={form.destination_city} onChange={handleChange} className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100">
                      <option value="">Select destination city</option>
                      {cityOptions.map((item) => (
                        <option key={item} value={item}>{item}</option>
                      ))}
                    </select>
                    {errors.destination_city && <p className="mt-1 text-sm text-red-600">{errors.destination_city}</p>}
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Departure Time</label>
                    <select name="departure_time" value={form.departure_time} onChange={handleChange} className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100">
                      <option value="">Select departure time</option>
                      {timeOptions.map((item) => (
                        <option key={item} value={item}>{item}</option>
                      ))}
                    </select>
                    {errors.departure_time && <p className="mt-1 text-sm text-red-600">{errors.departure_time}</p>}
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Arrival Time</label>
                    <select name="arrival_time" value={form.arrival_time} onChange={handleChange} className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100">
                      <option value="">Select arrival time</option>
                      {timeOptions.map((item) => (
                        <option key={item} value={item}>{item}</option>
                      ))}
                    </select>
                    {errors.arrival_time && <p className="mt-1 text-sm text-red-600">{errors.arrival_time}</p>}
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Stops</label>
                    <select name="stops" value={form.stops} onChange={handleChange} className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100">
                      <option value="">Select stop option</option>
                      {stopOptions.map((item) => (
                        <option key={item.value} value={item.value}>{item.label}</option>
                      ))}
                    </select>
                    {errors.stops && <p className="mt-1 text-sm text-red-600">{errors.stops}</p>}
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Class</label>
                    <select name="class" value={form.class} onChange={handleChange} className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100">
                      <option value="">Select class</option>
                      {classOptions.map((item) => (
                        <option key={item} value={item}>{item}</option>
                      ))}
                    </select>
                    {errors.class && <p className="mt-1 text-sm text-red-600">{errors.class}</p>}
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Duration (hours)</label>
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                      <input
                        type="range"
                        min="0.5"
                        max="24"
                        step="0.5"
                        value={Number(form.duration) || 5.5}
                        onChange={(event) => setForm((current) => ({ ...current, duration: event.target.value }))}
                        className="h-2 w-full cursor-pointer accent-brand-600"
                      />
                      <div className="mt-3 flex items-center justify-between gap-3">
                        <input
                          type="number"
                          step="0.5"
                          min="0.5"
                          max="24"
                          name="duration"
                          value={form.duration}
                          onChange={handleChange}
                          placeholder="5.5"
                          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                        />
                        <span className="whitespace-nowrap text-sm font-medium text-slate-500">hrs</span>
                      </div>
                    </div>
                    {errors.duration && <p className="mt-1 text-sm text-red-600">{errors.duration}</p>}
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Days Left</label>
                    <input type="number" min="1" name="days_left" value={form.days_left} onChange={handleChange} placeholder="20" className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />
                    {errors.days_left && <p className="mt-1 text-sm text-red-600">{errors.days_left}</p>}
                  </div>
                </div>

                <div className="flex flex-col gap-3 pt-2 sm:flex-row">
                  <button type="submit" disabled={isLoading} className="w-full rounded-full bg-brand-600 px-6 py-3 text-base font-semibold text-white shadow-soft transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-70 sm:w-auto">
                    {isLoading ? 'Analyzing your flight details...' : 'Predict Price'}
                  </button>
                  <button type="button" onClick={resetForm} className="w-full rounded-full border border-slate-200 bg-white px-6 py-3 text-base font-semibold text-slate-700 transition hover:border-brand-200 hover:text-brand-700 sm:w-auto">
                    Reset
                  </button>
                </div>

                {serverError && (
                  <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {serverError}
                  </div>
                )}
              </form>
            </div>

            <div className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-soft md:p-8">
              {isLoading && (
                <div className="flex h-full min-h-[280px] flex-col items-center justify-center text-center">
                  <div className="mb-4 h-14 w-14 animate-spin rounded-full border-4 border-brand-100 border-t-brand-600"></div>
                  <p className="text-lg font-semibold text-slate-900">Analyzing your flight details...</p>
                </div>
              )}

              {!isLoading && result && (
                <div className="flex h-full min-h-[280px] flex-col justify-center gap-4">
                  <p className="text-sm font-semibold uppercase tracking-[0.14em] text-brand-600">Estimated Flight Price</p>
                  <div className="text-4xl font-extrabold tracking-tight text-slate-900">₹{result.inr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
                  <p className="text-sm font-medium text-slate-500">Approximately:</p>
                  <div className="text-2xl font-bold text-brand-700">{result.jod.toFixed(0)} JOD</div>
                  {result.aiSummary && (
                    <p className="rounded-2xl bg-brand-50 p-3 text-sm leading-6 text-slate-700">{result.aiSummary}</p>
                  )}
                  <button onClick={resetForm} className="mt-2 inline-flex w-full items-center justify-center rounded-full bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-800">
                    Predict Another Flight
                  </button>
                  <button type="button" onClick={() => setChatOpen((curr) => !curr)} className="inline-flex w-full items-center justify-center rounded-full border border-brand-200 bg-brand-50 px-6 py-3 text-sm font-semibold text-brand-700 transition hover:bg-brand-100">
                    Ask AI assistant
                  </button>
                </div>
              )}

              {!isLoading && !result && (
                <div className="flex h-full min-h-[280px] flex-col items-center justify-center rounded-3xl border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                  <div className="mb-4 rounded-2xl bg-brand-50 p-4 text-3xl">🧭</div>
                  <h3 className="text-xl font-semibold text-slate-900">Ready to estimate your flight?</h3>
                  <p className="mt-2 max-w-sm text-sm text-slate-600">
                    Fill in your trip details and we’ll estimate the ticket price using the trained model.
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="mt-8 rounded-[28px] border border-brand-100 bg-brand-50/50 p-6 shadow-soft md:p-8">
            <div className="mb-6 max-w-2xl">
              <p className="text-sm font-semibold uppercase tracking-[0.12em] text-brand-600">Trip planner</p>
              <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">Add context for your trip</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Optional details help the AI assistant tailor travel tips, packing ideas, and destination suggestions. They are not required for the price estimate.
              </p>
            </div>

            <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Flight code</label>
                <input name="flight" value={form.flight} onChange={handleChange} placeholder="Optional flight code" className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Travel month</label>
                <select name="month" value={form.month} onChange={handleChange} className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100">
                  <option value="">Select month</option>
                  {monthOptions.map((item) => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Public holiday?</label>
                <select name="holiday" value={form.holiday} onChange={handleChange} className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100">
                  <option value="">Select option</option>
                  {holidayOptions.map((item) => (
                    <option key={item.value} value={item.value}>{item.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Trip purpose</label>
                <select name="trip_purpose" value={form.trip_purpose} onChange={handleChange} className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100">
                  <option value="">Select purpose</option>
                  {tripPurposeOptions.map((item) => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </section>

        {result && chatOpen && (
          <section id="ai-assistant" className="mx-auto mt-8 max-w-4xl px-4 pb-16 md:px-8">
            <div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-soft md:p-6">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-[0.12em] text-brand-600">AI Assistant</p>
                  <h3 className="mt-1 text-xl font-bold text-slate-900">Trip help</h3>
                </div>
              </div>

              <div className="max-h-80 space-y-3 overflow-y-auto rounded-2xl bg-slate-50 p-4">
                {chatMessages.length === 0 && (
                  <div className="text-sm text-slate-500">Ask about places to visit, food, travel tips, or packing.</div>
                )}
                {chatMessages.map((message, index) => (
                  <div key={`${message.role}-${index}`} className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm leading-6 ${message.role === 'user' ? 'ml-auto bg-brand-600 text-white' : 'bg-white text-slate-700 border border-slate-200'}`}>
                    {message.text}
                  </div>
                ))}
                {chatLoading && <div className="text-sm text-slate-500">Assistant is thinking...</div>}
              </div>

              <form onSubmit={submitChatMessage} className="mt-4 flex gap-3">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(event) => setChatInput(event.target.value)}
                  placeholder="Ask about your trip..."
                  className="flex-1 rounded-full border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                />
                <button type="submit" disabled={chatLoading || !chatInput.trim()} className="rounded-full bg-brand-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60">
                  Send
                </button>
              </form>

              {chatError && <div className="mt-3 text-sm text-red-600">{chatError}</div>}
            </div>
          </section>
        )}

        <section id="about" className="mx-auto max-w-6xl px-4 py-16 md:px-8">
          <div className="mb-10 text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.12em] text-brand-600">How It Works</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">Travel with more confidence</h2>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {[
              { step: '01', title: 'Enter Flight Details', description: 'Provide your airline, route, class, timing, duration, and days left.', icon: '📝' },
              { step: '02', title: 'AI Analyzes Your Trip', description: 'The trained Random Forest regression model processes your flight information.', icon: '🤖' },
              { step: '03', title: 'Get Your Estimated Price', description: 'Receive an estimated ticket price instantly.', icon: '💸' },
            ].map((item) => (
              <div key={item.step} className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-soft">
                <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-2xl">{item.icon}</div>
                <p className="text-sm font-semibold uppercase tracking-[0.12em] text-brand-600">{item.step} — {item.title}</p>
                <p className="mt-4 text-base leading-7 text-slate-600">{item.description}</p>
              </div>
            ))}
          </div>

          <div className="mt-12 rounded-[28px] border border-slate-200 bg-white p-8 shadow-soft">
            <p className="text-sm font-semibold uppercase tracking-[0.12em] text-brand-600">About the Model</p>
            <h3 className="mt-2 text-2xl font-bold text-slate-900">Estimated Price — not a guaranteed booking price.</h3>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
              FlyPrice AI uses a Random Forest Regression model trained on historical flight-price data. The model learns relationships between flight characteristics and ticket prices and uses those patterns to estimate the price of a new flight.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
