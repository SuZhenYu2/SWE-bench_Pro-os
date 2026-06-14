import login

def test_login_success():
    assert login.login("admin", "123456") == True

def test_login_wrong_password():
    assert login.login("admin", "wrong") == False

def test_login_wrong_username():
    assert login.login("user", "123456") == False

if __name__ == "__main__":
    test_login_success()
    test_login_wrong_password()
    test_login_wrong_username()
    print("All tests passed!")
