from flask import Flask, flash, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from products import men_products, women_products, kids_products

app = Flask(__name__)
app.secret_key = '65c15da967de6cbed731167da57e2733'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# ------------------ User Model ------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# ------------------ Address Model ------------------

class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    house = db.Column(db.String(255), nullable=False)
    area = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', backref=db.backref('addresses', lazy=True))

# ------------------ NEW: Order Models ------------------

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = db.relationship('User', backref=db.backref('orders', lazy=True))
    address = db.relationship('Address')
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_category = db.Column(db.String(20), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    size = db.Column(db.String(10), nullable=False)
    price = db.Column(db.Float, nullable=False)
    cancelled = db.Column(db.Boolean, default=False)  # 👈 New field


# ------------------ Authentication Routes ------------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user:
            return redirect(url_for('login'))

        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('signup.html', title="ShoeVerse - Signup")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if not user:
            return redirect(url_for('signup'))

        if user.password == password:
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash("Logged in successfully!", "success")
            return redirect(url_for('account'))
        else:
            flash("Incorrect password.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html', title="ShoeVerse - Login")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ------------------ Product Website Routes ------------------

@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html', title="ShoeVerse - Trendy Footwear for Everyone")

@app.route('/login/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('account.html', title="ShoeVerse - Account", user_name=session.get('user_name'))

@app.route('/account/account_overview')
def account_overview():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if 'user_name' not in session:
        user = User.query.get(session['user_id'])
        if user:
            session['user_name'] = user.name

    return render_template('account_overview.html', title="Account Overview")


@app.route('/products/<category>')
def product(category):
    if category == "men":
        products = men_products
        title = "ShoeVerse - Men's Collection"
    elif category == "women":
        products = women_products
        title = "ShoeVerse - Women's Collection"
    elif category == "kids":
        products = kids_products
        title = "ShoeVerse - Kid's Collection"
    else:
        return "Category not found", 404

    return render_template("products.html", title=title, prod=products, category=category)

# ------------------ Product Detail Route ------------------

@app.route('/product/<category>/<int:product_id>')
def product_detail(category, product_id):
    if category == "men":
        products = men_products
    elif category == "women":
        products = women_products
    elif category == "kids":
        products = kids_products
    else:
        return "Category not found", 404

    product = products.get(product_id)
    if not product:
        return "Product not found", 404

    # Check if product is in wishlist
    wishlist = session.get('wishlist', [])
    in_wishlist = {'category': category, 'id': product_id} in wishlist

    return render_template("product_detail.html", title=product['name'], product=product,
                           category=category, product_id=product_id, in_wishlist=in_wishlist)



# ------------------ Wishlist Routes ------------------

@app.route('/add_to_wishlist/<category>/<int:product_id>')
def add_to_wishlist(category, product_id):
    wishlist = session.get('wishlist', [])
    item = {'category': category, 'id': product_id}
    if item not in wishlist:
        wishlist.append(item)
        session['wishlist'] = wishlist
    return redirect(request.referrer)

@app.route('/wishlist')
def wishlist():
    wishlist = session.get('wishlist', [])
    products = []

    for item in wishlist:
        category = item['category']
        product_id = item['id']
        product = None

        if category == 'men':
            product = men_products.get(product_id)
        elif category == 'women':
            product = women_products.get(product_id)
        elif category == 'kids':
            product = kids_products.get(product_id)

        if product:
            products.append({'id': product_id, 'category': category, **product})

    return render_template('wishlist.html', title="ShoeVerse - Wishlist", products=products)

@app.route('/remove_from_wishlist/<category>/<int:product_id>')
def remove_from_wishlist(category, product_id):
    wishlist = session.get('wishlist', [])
    item = {'category': category, 'id': product_id}
    if item in wishlist:
        wishlist.remove(item)
        session['wishlist'] = wishlist
    return redirect(url_for('wishlist'))


# ------------------ Address Routes ------------------

@app.route('/account/address', methods=['GET', 'POST'])
def address():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    existing_address = Address.query.filter_by(user_id=user_id).first()

    if request.method == 'POST':
        full_name = request.form['full_name']
        phone_number = request.form['phone_number']
        pincode = request.form['pincode']
        state = request.form['state']
        city = request.form['city']
        house = request.form['house']
        area = request.form['area']

        if existing_address:
            existing_address.full_name = full_name
            existing_address.phone_number = phone_number
            existing_address.pincode = pincode
            existing_address.state = state
            existing_address.city = city
            existing_address.house = house
            existing_address.area = area
        else:
            new_address = Address(
                full_name=full_name,
                phone_number=phone_number,
                pincode=pincode,
                state=state,
                city=city,
                house=house,
                area=area,
                user_id=user_id
            )
            db.session.add(new_address)

        db.session.commit()
        return redirect(url_for('address'))  # redirects back to GET view

    return render_template('address_view.html', address=existing_address, title="ShoeVerse - Your Address")

@app.route('/edit_address', methods=['GET', 'POST'])    
def edit_address():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    existing_address = Address.query.filter_by(user_id=user_id).first()

    return render_template('address.html', address=existing_address, title="ShoeVerse - Edit Address")

@app.route('/delete_address', methods=['POST'])
def delete_address():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to delete address.', 'warning')
        return redirect(url_for('login'))

    address = Address.query.filter_by(user_id=user_id).first()
    if address:
        db.session.delete(address)
        db.session.commit()
        flash('Address deleted successfully.', 'success')
    else:
        flash('No address found to delete.', 'danger')

    return redirect(url_for('account'))


# ------------------ Cart Routes ------------------

@app.route('/add_to_cart/<category>/<int:product_id>')
def add_to_cart(category, product_id):
    size = request.args.get('size')
    if not size:
        return jsonify({'success': False, 'message': 'Please select a size.'})

    cart = session.get('cart', [])

    for item in cart:
        if item['category'] == category and item['id'] == product_id and item['size'] == size:
            item['quantity'] += 1
            break
    else:
        cart.append({'category': category, 'id': product_id, 'quantity': 1, 'size': size})

    session['cart'] = cart
    return jsonify({'success': True, 'message': 'Product added to cart.'})


@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Please log in to view your cart.', 'warning')
        return redirect(url_for('login'))

    cart = session.get('cart', [])
    products = []
    subtotal = 0

    for item in cart:
        category = item['category']
        product_id = item['id']
        quantity = item['quantity']
        product = None

        if category == 'men':
            product = men_products.get(product_id)
        elif category == 'women':
            product = women_products.get(product_id)
        elif category == 'kids':
            product = kids_products.get(product_id)

        if product:
            total_price = product['price'] * quantity
            subtotal += total_price
            products.append({
             'id': product_id,
             'category': category,
             'name': product['name'],
             'price': product['price'],
             'quantity': quantity,
             'image': product['image'],
             'total_price': total_price,
             'size': item['size']
        })

    return render_template('cart.html', title="ShoeVerse - Cart", products=products, subtotal=subtotal)

@app.route('/remove_from_cart/<category>/<int:product_id>/<size>')
def remove_from_cart(category, product_id, size):
    cart = session.get('cart', [])
    for item in cart:
        if item['category'] == category and item['id'] == product_id and item['size'] == size:
            cart.remove(item)
            break
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/update_quantity/<category>/<int:product_id>/<size>', methods=['POST'])
def update_quantity(category, product_id, size):
    action = request.form['action']
    cart = session.get('cart', [])

    for item in cart:
        if item['category'] == category and item['id'] == product_id and item['size'] == size:
            if action == 'increase':
                item['quantity'] += 1
            elif action == 'decrease' and item['quantity'] > 1:
                item['quantity'] -= 1
            break

    session['cart'] = cart
    return redirect(url_for('cart'))


# ------------------ Search Functionality ------------------

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').lower()
    results = []

    all_products = []
    for category, products in [('men', men_products), ('women', women_products), ('kids', kids_products)]:
        for id, product in products.items():
            product_copy = product.copy()
            product_copy['id'] = id
            product_copy['category'] = category
            all_products.append(product_copy)

    for product in all_products:
        if query in product['name'].lower():
            results.append({
                'id': product['id'],
                'category': product['category'],
                'name': product['name'],
                'image': url_for('static', filename=product['image']),
                'price': product['price']
            })

    return jsonify(results[:5])

# ------------------ NEW: Checkout Route ------------------

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash("Please login to proceed to checkout.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    addresses = Address.query.filter_by(user_id=user_id).all()
    cart = session.get('cart', [])

    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for('cart'))

    if request.method == 'POST':
        # Validate payment method
        payment_method = request.form.get('payment_method')
        if not payment_method:
            flash("Please select a payment method.", "warning")
            return redirect(url_for('checkout'))

        if payment_method != 'cod':
            flash("Currently only Cash On Delivery is supported.", "danger")
            return redirect(url_for('checkout'))

        # Validate address
        if not addresses:
            flash("Please add your address before placing an order.", "warning")
            return redirect(url_for('address'))

        selected_address_id = request.form.get('address')
        if not selected_address_id:
            flash("Please select an address.", "warning")
            return redirect(url_for('checkout'))

        # Create order
        order = Order(
            user_id=user_id,
            address_id=int(selected_address_id),
            payment_method=payment_method
        )
        db.session.add(order)
        db.session.flush()  # get order.id before commit

        # Add order items
        for item in cart:
            category = item['category']
            prod_id = item['id']
            quantity = item['quantity']
            size = item['size']

            if category == 'men':
                product = men_products.get(prod_id)
            elif category == 'women':
                product = women_products.get(prod_id)
            elif category == 'kids':
                product = kids_products.get(prod_id)
            else:
                continue

            if product:
                order_item = OrderItem(
                    order_id=order.id,
                    product_category=category,
                    product_id=prod_id,
                    quantity=quantity,
                    size=size,
                    price=product['price']
                )
                db.session.add(order_item)

        db.session.commit()
        session['cart'] = []  # Clear cart after order placed

        flash("Order placed successfully!", "success")
        return redirect(url_for('order_confirmation', order_id=order.id))

    return render_template('checkout.html', addresses=addresses, cart=cart, title="Checkout - ShoeVerse")

# --------------order confirmation route-----------------

@app.route('/order/confirmation/<int:order_id>')
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    order_items = OrderItem.query.filter_by(order_id=order_id).all()

    return render_template(
        'order_confirmation.html',
        order=order,
        items=order_items,
        title="Order Confirmation - ShoeVerse"
    )
    
# ------------------Order details-----------------------------

@app.route('/account/orders')
def orders():
    if 'user_id' not in session:
        flash("Please login to view your orders.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.id.desc()).all()

    # Attach product info to each order item
    for order in orders:
        for item in order.items:
            if item.product_category == 'men':
                product = men_products.get(item.product_id)
            elif item.product_category == 'women':
                product = women_products.get(item.product_id)
            elif item.product_category == 'kids':
                product = kids_products.get(item.product_id)
            else:
                product = None

            item.product_details = product  # Attach to item

    return render_template('orders.html', orders=orders, title="My Orders - ShoeVerse")

# -------------------Clear Order History----------------------
@app.route('/clear_order_history', methods=['POST'])
def clear_order_history():
    if 'user_id' not in session:
        flash("Please login to clear order history.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    orders = Order.query.filter_by(user_id=user_id).all()
    deleted_count = 0

    for order in orders:
        if all(item.cancelled for item in order.items):
            # Delete all order items
            for item in order.items:
                db.session.delete(item)

            # Only delete the order (not the address)
            db.session.delete(order)
            deleted_count += 1

    db.session.commit()

    if deleted_count:
        flash(f"{deleted_count} cancelled order(s) cleared.", "success")
    else:
        flash("No fully cancelled orders to clear.", "info")

    return redirect(url_for('orders'))


# --------------------Cancel order----------------------------
@app.route('/cancel_order_item/<int:item_id>', methods=['POST'])
def cancel_order_item(item_id):
    if 'user_id' not in session:
        flash("Please login to cancel items.", "warning")
        return redirect(url_for('login'))

    order_item = OrderItem.query.get(item_id)

    if not order_item:
        flash("Order item not found.", "danger")
        return redirect(url_for('orders'))

    order = order_item.order

    if order.user_id != session['user_id']:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('orders'))

    # ✅ Mark item as cancelled
    order_item.cancelled = True

    db.session.commit()
    flash("Item cancelled successfully.", "success")
    return redirect(url_for('orders'))


# ------------------ Global Template Context ------------------

@app.context_processor
def inject_user_name():
    user_name = session.get('user_name')
    return dict(user_name=user_name)

with app.app_context():
    try:
        db.session.execute(db.text("ALTER TABLE order_item ADD COLUMN cancelled BOOLEAN DEFAULT 0"))
        db.session.commit()
        print("✅ 'cancelled' column added successfully.")
    except Exception as e:
        if "duplicate column name" in str(e):
            print("⚠️ Column already exists. Skipping.")
        else:
            print("❌ Error while adding 'cancelled' column:", e)



# ------------------ Run the App ------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        #  Attempt to add the 'cancelled' column if not already present
        try:
            db.session.execute(db.text("ALTER TABLE order_item ADD COLUMN cancelled BOOLEAN DEFAULT 0"))
            db.session.commit()
            print("✅ 'cancelled' column added successfully.")
        except Exception as e:
            if "duplicate column name" in str(e):
                print("⚠️ Column already exists. Skipping.")
            else:
                print("❌ Error while adding 'cancelled' column:", e)

    app.run(host='0.0.0.0', port=5000, debug=True)
