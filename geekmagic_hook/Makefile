INSTALL_DIR := $(HOME)/.geekmagic_hook
SCRIPT      := geekmagic_hook.py
BINARY      := $(INSTALL_DIR)/geekmagic_hook
THEMES_SRC  := themes
THEMES_DST  := $(INSTALL_DIR)/themes

.PHONY: install uninstall clean

install:
	@echo "Installing geekmagic_hook to $(INSTALL_DIR)…"
	@mkdir -p $(INSTALL_DIR)
	@cp $(SCRIPT) $(BINARY)
	@chmod +x $(BINARY)
	@cp -rn $(THEMES_SRC)/. $(THEMES_DST)/ 2>/dev/null || true
	@echo "✓ Installed: $(BINARY)"
	@echo ""
	@echo "Next: run '$(BINARY) setup' to configure"

uninstall:
	@echo "Uninstalling geekmagic_hook…"
	@$(BINARY) uninstall 2>/dev/null || true
	@rm -f $(BINARY)
	@echo "✓ Binary removed (config and logs preserved in $(INSTALL_DIR))"

clean:
	@rm -f $(BINARY)
	@rm -rf $(INSTALL_DIR)/logs
	@echo "✓ Cleaned"
