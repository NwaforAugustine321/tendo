-- User profiles
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Business profiles
CREATE TABLE IF NOT EXISTS business_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES user_profiles(id),
    name TEXT NOT NULL,
    category TEXT DEFAULT 'product',
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Customers
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    type TEXT DEFAULT 'customer',
    balance NUMERIC(12,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Products
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    name TEXT NOT NULL,
    unit TEXT,
    unit_price NUMERIC(12,2),
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Services
CREATE TABLE IF NOT EXISTS services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    name TEXT NOT NULL,
    price NUMERIC(12,2),
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Inventory
CREATE TABLE IF NOT EXISTS inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    product_id UUID REFERENCES products(id),
    quantity NUMERIC(12,2) DEFAULT 0,
    reorder_level NUMERIC(12,2),
    last_updated TIMESTAMPTZ DEFAULT now()
);

-- Inventory movements
CREATE TABLE IF NOT EXISTS inventory_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    inventory_id UUID NOT NULL REFERENCES inventory(id),
    movement_type TEXT NOT NULL,
    quantity NUMERIC(12,2) NOT NULL,
    reference TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Transactions
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    customer_id UUID REFERENCES customers(id),
    type TEXT NOT NULL,
    payment_type TEXT,
    total NUMERIC(12,2) NOT NULL,
    status TEXT DEFAULT 'completed',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Invoices
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    invoice_number TEXT,
    total NUMERIC(12,2) NOT NULL,
    status TEXT DEFAULT 'pending',
    due_date DATE,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Invoice line items
CREATE TABLE IF NOT EXISTS invoice_line_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    description TEXT NOT NULL,
    quantity NUMERIC(12,2) NOT NULL,
    unit_price NUMERIC(12,2) NOT NULL,
    total NUMERIC(12,2) NOT NULL
);

-- Payments
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    invoice_id UUID REFERENCES invoices(id),
    customer_id UUID REFERENCES customers(id),
    amount NUMERIC(12,2) NOT NULL,
    payment_method TEXT,
    reference TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Ledger entries
CREATE TABLE IF NOT EXISTS ledger_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    transaction_id UUID NOT NULL REFERENCES transactions(id),
    entry_type TEXT NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    account TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- AI Business Understanding
CREATE TABLE IF NOT EXISTS ai_business_understanding (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    summary TEXT NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 0.5 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    evidence_count INTEGER DEFAULT 0,
    evidence_references JSONB DEFAULT '[]',
    correction_history JSONB DEFAULT '[]',
    evolution_history JSONB DEFAULT '[]',
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'retired')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Business evidence
CREATE TABLE IF NOT EXISTS business_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    understanding_id UUID NOT NULL REFERENCES ai_business_understanding(id),
    evidence_type TEXT NOT NULL CHECK (evidence_type IN ('confirmation', 'correction', 'observation')),
    source_reference JSONB NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Conversation sessions
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    user_id UUID NOT NULL REFERENCES user_profiles(id),
    title TEXT NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Conversation messages
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id),
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'text',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Operation checkpoints
CREATE TABLE IF NOT EXISTS operation_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id),
    message_id UUID REFERENCES conversation_messages(id),
    operation_type TEXT NOT NULL,
    user_input TEXT NOT NULL,
    ai_understanding_summary TEXT,
    before_state JSONB NOT NULL,
    after_state JSONB NOT NULL,
    status TEXT DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'reverted')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    user_id UUID NOT NULL REFERENCES user_profiles(id),
    operation_type TEXT NOT NULL,
    affected_entity JSONB NOT NULL,
    status TEXT DEFAULT 'success',
    failure_reason TEXT,
    event_id TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS on all tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE services ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_line_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE ledger_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_business_understanding ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE operation_checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- RLS policies (service role bypasses, but these protect direct access)
CREATE POLICY "users_own_profile" ON user_profiles FOR ALL USING (id = auth.uid());
CREATE POLICY "users_own_businesses" ON business_profiles FOR ALL USING (user_id = auth.uid());
CREATE POLICY "business_scope" ON customers FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON products FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON services FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON inventory FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON inventory_movements FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON transactions FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON invoices FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON invoice_line_items FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON payments FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON ledger_entries FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON ai_business_understanding FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON business_evidence FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON conversation_sessions FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON conversation_messages FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON operation_checkpoints FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON audit_logs FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
